# sfacg_metadata_crawler

SFACG (sfacg.com) 小说元数据爬取与入库工具。

## 架构

```
output/          CI 每日产出的 JSONL 数据集（只读）
meta_spider/     Scrapy 爬虫（遗留代码，只读）
database/
  enums.py        枚举定义（Genre / Status / PType），含 label <-> enum 双向映射
  models.py       SQLModel ORM 模型（Novel / Author / Tag / Contest / Banner）
  engine.py       数据库引擎配置（SQLite + 可选云端）
  app.py          建表工具
  cleaner.py      数据清洗（去重、类型转换、URL 压缩）
  writer.py       数据库写入（批量 upsert、新增/更新分发）
  cloud.py        云端同步（分块写入、重试机制）
ingest.py        三阶段流水线编排（并行清洗 -> SQLite -> 云端）
```

## CI 工作流

每日自动执行：

```bash
# 1. 爬取元数据
scrapy runspider meta_spider/spiders/meta_spider.py -o output/meta.jsonl

# 2. 入库
uv run ingest.py output/meta.jsonl
```

入库为幂等操作（按 `nid` upsert），重复执行不会产生重复数据。

## 使用

```bash
# 导入指定文件
uv run ingest.py output/meta.jsonl

# 导入所有待处理文件
uv run ingest.py
```

## Ingest 工作原理

`ingest.py` 是整个项目的核心，负责将爬虫产出的 JSONL 文件清洗后写入数据库。整体分为三个阶段，按顺序执行：

### 三阶段流水线

```
Phase 1: 并行加载清洗          Phase 2: 顺序写入 SQLite        Phase 3: 同步云端
┌─────────────────────┐      ┌──────────────────────────┐     ┌──────────────────────┐
│ ThreadPoolExecutor   │      │ 逐文件 commit_dataframe() │     │ _sync_to_cloud()     │
│                      │      │                          │     │                      │
│ file1 -> load+clean  │      │ 1. 填充关联表 (批量upsert)│     │ 10k行/chunk          │
│ file2 -> load+clean  │      │ 2. 按nid拆分新增/更新     │     │ 独立事务 + 重试3次    │
│ file3 -> load+clean  │      │ 3. bulk insert / update  │     │ 指数退避             │
│          ...         │      │                          │     │                      │
└─────────────────────┘      └──────────────────────────┘     └──────────────────────┘
```

### Phase 1：数据清洗（`load_and_clean`）

每个 JSONL 文件经 pandas 读入后，执行以下清洗步骤：

1. **按 `nid` 去重** — 同一个 `nid` 出现多次时，保留 `last_update` 最新的一条
2. **数值列填充** — `click_num`、`word_num` 等缺失值填 0 并转 int
3. **时间列转换** — `last_update` 用 `pd.to_datetime` 解析，无效值变为 NaT（入库时为 NULL）
4. **空字符串归一化** — `cover`、`banner`、`contest` 的空串/NaN 统一为 `None`
5. **URL 压缩** — `cover` 去除 CDN 前缀 `http://rs.sfacg.com/web/novel/images/NovelCover/Big/`；`banner` 仅保留查询参数部分（前缀和 nid 可还原）
6. **tags 清理** — 非 list 类型的 tags 统一为空 list
7. **过滤无效行** — `author` 为空的行直接丢弃

### Phase 2：写入 SQLite（`commit_dataframe`）

每个清洗后的 DataFrame 在一个数据库事务内完成写入，保证原子性。`commit_dataframe` 内部又分为三个子阶段：

#### 2a. 批量填充关联表（`_batch_upsert`）

Author、Contest、Tag 采用统一的批量 upsert 策略：1 次 SELECT 查出已存在的记录 + 1 次 bulk INSERT 写入缺失项 + 1 次 SELECT 回查新 ID。相比逐行 add()，大幅减少数据库往返。

#### 2b. 按 nid 拆分为新增/更新

查询 `Novel` 表中已存在的 nid，将 DataFrame 分为 `df_new`（INSERT）和 `df_old`（UPDATE）。`known_nids` 作为跨文件缓存传入，避免重复查询已确认存在的 nid。

#### 2c. 分别处理新增与更新

- **新增（`_insert_novels`）**：将构建好的 Novel 字典列表通过 `sa_insert` 一次性 bulk INSERT。同时写入 Banner 和 NovelTagLink（先删旧的 tag 关联再插入新的）。
- **更新（`_update_novels`）**：使用 `sa_update` + `bindparam` 批量更新所有字段，避免逐行 UPDATE 的性能开销。

两步中都会检测枚举降级（如 Genre 中出现了不认识的分类名被映射为 OTHER），将降级的 nid 收集起来写入 `OTHER.txt`。

### Phase 3：云端同步（`_sync_to_cloud`）

当环境变量中配置了云端数据库连接信息（DB_TYPE、DB_HOST 等）时，将全部 DataFrame 拼接后按 **10,000 行/chunk** 分批写入云端。每 chunk 为独立事务，失败时最多重试 3 次，退避延迟为 2^attempt 秒。chunk 间间隔 0.1 秒防止限流。

### 字段映射

| JSONL 字段 | 目标 | 映射方式 |
|---|---|---|
| `nid` | Novel.id | 直接 |
| `novel_title` | Novel.title | 直接 |
| `author` | Author.name | 查找或创建 |
| `price_type_id` | Novel.ptype | `0 -> 免费 -> FREE`, `1 -> 签约 -> SIGN`, `2 -> VIP -> VIP` |
| `genre` | Novel.genre | 中文名 -> Genre 枚举（未匹配降级为 OTHER=99） |
| `status_id` | Novel.status | `0 -> 已完结 -> FINISHED`, `1 -> 连载中 -> ON_GOING`, `2 -> 断更 -> DIED` |
| `contest` | Contest.name | 非空时查找或创建 |
| `tags` | Tag (M2M) | 批量查找或创建，通过 NovelTagLink 关联 |
| `banner` | Banner.url | 压缩存储（仅保留查询参数） |
| `cover` | Novel.cover | 去除 CDN 前缀，默认封面（defaultNew.jpg）存为 NULL |

### 枚举值（DB 中存储整数值）

| Genre | Status | PType |
|---|---|---|
| MAGIC = 1 (魔幻) | FINISHED = 1 (已完结) | FREE = 1 (免费) |
| FANTASY = 2 (玄幻) | ON_GOING = 2 (连载中) | SIGN = 2 (签约) |
| ANCIENT = 3 (古风) | DIED = 3 (断更) | VIP = 3 (VIP) |
| SF = 4 (科幻) | ACTIVE_F = 4 (完结活跃) | OTHER = 99 |
| SCHOOL = 5 (校园) | ACTIVE_D = 5 (断更活跃) | |
| URBAN = 6 (都市) | OTHER = 99 | |
| GAME = 7 (游戏) | | |
| DOUJIN = 8 (同人) | | |
| MYSTERY = 9 (悬疑) | | |
| OTHER = 99 | | |

未匹配的值自动降级为 `OTHER (99)`。

### 输出文件

| 文件 | 内容 |
|---|---|
| `LOG.txt` | 每次运行的日志：文件级统计、云端同步结果、总耗时 |
| `OTHER.txt` | 枚举降级为 OTHER 的 nid 列表，用于人工排查新增分类 |
