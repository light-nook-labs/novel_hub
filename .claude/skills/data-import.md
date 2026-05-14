---
name: data-import
description: |
  使用 pandas 清洗 output 目录中的 JSONL 数据集，并通过 SQLModel ORM 入库。
  触发：数据导入、数据清洗、入库、jsonl导入数据库、output目录数据处理。
---

# 数据清洗与入库

## 核心流程

1. **读取数据**：遍历 `output/` 目录下所有 `.jsonl` 文件，用 pandas 读取并合并
2. **清洗数据**：去重、缺失值处理、类型转换
3. **字段映射**：先将 JSONL 中的数字 ID 转换为 `constants.py` 列表的字符串值（如 `0 → '免费'`），再通过字符串 label 映射到 `enums.py` 中的枚举值。这样即使 `constants.py` 弃用，映射关系也不会断裂
4. **入库**：使用 `models.py` 中定义的 SQLModel ORM 写入 SQLite 数据库

## 字段映射规则

原始 JSONL 字段 → ORM 模型字段：

| JSONL 字段 | 模型 | 字段 | 映射方式 |
|-----------|------|------|---------|
| nid | Novel | id | 直接使用 |
| novel_title | Novel | title | 直接使用 |
| author | Author | name | 查找或创建 |
| price_type_id | Novel | ptype | 索引 → 字符串 → 枚举：`0→'免费'→PType.FREE`, `1→'签约'→PType.SIGN`, `2→'VIP'→PType.VIP` |
| genre | Novel | genre | 已是中文字符串，直接查找 `GENRE_LABEL_MAP` → 枚举 |
| status_id | Novel | status | 索引 → 字符串 → 枚举：`0→'已完结'→Status.FINISHED`, `1→'连载中'→Status.ON_GOING`, `2→'断更'→Status.DIED` |
| click_num | Novel | click_num | 直接使用 |
| word_num | Novel | word_num | 直接使用 |
| praise_num | Novel | praise_num | 直接使用 |
| like_num | Novel | like_num | 直接使用 |
| last_update | Novel | last_update | 转换为 datetime |
| cover | Novel | cover | 直接使用 |
| banner | Banner | url | 非空字符串时创建 |
| tags | Tag (M2M) | name | 查找或创建，通过 NovelTagLink 关联 |
| contest | Contest | name | 非空时查找或创建 |

## 关键映射（两步走：ID → 字符串 → 枚举）

JSONL 中的 `price_type_id` 和 `status_id` 是 `constants.py` 旧列表的索引。
因 `constants.py` 计划弃用，先将 ID 转换为字符串 label，再通过枚举的 `from_label()` 方法映射。

```python
from enums import Genre, Status, PType

# ── 第一步：ID → 字符串 label（硬编码，不再依赖 constants.py） ──────
PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}

# ── 第二步：字符串 label → 枚举（使用枚举内置的 from_label） ──────
# ptype = PType.from_label(PRICE_TYPE_ID_TO_LABEL.get(row["price_type_id"], "其他"))
# status = Status.from_label(STATUS_ID_TO_LABEL.get(row["status_id"], "其他"))
# genre = Genre.from_label(row["genre"])   # genre 字段已是中文，直接映射

# ⚠️ from_label() 返回枚举成员（如 PType.FREE），赋值给 Novel.int 字段时
# SQLModel 自动取其 .value（整数）存入数据库。
# DB 中存储的是枚举的整数值，不是字符串！
```

## 数据库

- 统一使用 `db.py` 中的 `sqlite_engine`，**不要再自行创建 engine**
- 数据库文件：`database.db`（由 `db.py` 定义）
- 建表：`SQLModel.metadata.create_all(sqlite_engine)`
- 操作：`from sqlmodel import Session` + `Session(sqlite_engine)` 进行批量插入

```python
from db import sqlite_engine
from sqlmodel import Session, SQLModel

SQLModel.metadata.create_all(sqlite_engine)

with Session(sqlite_engine) as session:
    ...
    session.commit()
```

## pandas 清洗要点

- 按 `nid` 去重，保留 `last_update` 最新的记录
- `cover` 为 `null` 或空字符串时设为 None
- `banner` 为空字符串时跳过，不创建 Banner 记录
- `contest` 为空字符串时不关联 Contest
- `tags` 为 `null` 或空列表时跳过关联
- `author` 为空时跳过该条记录（必填字段）
- `click_num`, `word_num`, `praise_num`, `like_num` 转为 int，缺失填 0
- `last_update` 转为 datetime，无效格式填当前时间
