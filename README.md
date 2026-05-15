# sfacg_metadata_crawler

SFACG (sfacg.com) 小说元数据爬取与入库工具。

## 架构

```
output/          CI 每日产出的 JSONL 数据集（只读）
meta_spider/     Scrapy 爬虫（遗留代码，只读）
enums.py         枚举定义（Genre / Status / PType），含 label ↔ enum 双向映射
models.py        SQLModel ORM 模型（Novel / Author / Tag / Contest / Banner）
db.py            数据库引擎配置（SQLite）
ingest.py   pandas 清洗 → ORM 入库
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

## 数据清洗

`ingest.py` 在入库前自动执行：

- 按 `nid` 去重，保留 `last_update` 最新记录
- 缺失数值填 0，无效日期填当前时间
- 空字符串 / NaN 统一为 `None`
- author 为空的行直接跳过
- URL 压缩：去除 CDN 前缀（cover ~50%，banner ~90%）

## 字段映射

| JSONL 字段 | 目标 | 映射方式 |
|---|---|---|
| `nid` | Novel.id | 直接 |
| `novel_title` | Novel.title | 直接 |
| `author` | Author.name | 查找或创建 |
| `price_type_id` | Novel.ptype | `0→免费→FREE`, `1→签约→SIGN`, `2→VIP→VIP` |
| `genre` | Novel.genre | 中文名 → Genre 枚举 |
| `status_id` | Novel.status | `0→已完结→FINISHED`, `1→连载中→ON_GOING`, `2→断更→DIED` |
| `contest` | Contest.name | 非空时查找或创建 |
| `tags` | Tag (M2M) | 批量查找或创建，通过 NovelTagLink 关联 |
| `banner` | Banner.url | 压缩存储（仅保留查询参数） |
| `cover` | Novel.cover | 去除 CDN 前缀 |

## 枚举值（DB 中存储整数值）

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
