---
name: data-import
description: "Use when importing JSONL novel metadata into the database. Triggers: 数据导入, 数据清洗, 入库, jsonl导入数据库, output目录数据处理, 填充数据库."
metadata:
  version: "1.0.0"
---

# 数据清洗与入库

## Core Principles

**1. output/ is read-only.** JSONL files are CI artifacts — read from them, never write or delete.

**2. SQLite first, cloud best-effort.** Local SQLite always committed first and is the source of truth. Cloud sync happens after and may fail without affecting local data integrity.

**3. Atomic per-engine transactions.** Each `commit_dataframe` call is a single transaction with explicit rollback on failure.

**4. Upsert by nid.** All imports are idempotent — existing novels are updated, new novels are inserted.

## CLI Usage

```bash
# Import all files in output/
uv run main.py

# Import a specific file (CI daily workflow)
uv run main.py output/meta.jsonl
```

## Data Flow

```
output/*.jsonl -> load_and_clean() -> commit_dataframe(sqlite) -> _sync_to_cloud(df)
                                           |                            |
                                      SQLite (atomic)            cloud_engine (retry x3)
```

## Field Mapping

JSONL fields -> ORM models (two-step: ID -> label -> enum):

| JSONL field | Model | Column | Mapping |
|---|---|---|---|
| nid | Novel | id | Direct |
| novel_title | Novel | title | Direct |
| author | Author | name | Find or create |
| price_type_id | Novel | ptype | 0->免费->PType.FREE, 1->签约->PType.SIGN, 2->VIP->PType.VIP |
| genre | Novel | genre | Chinese name -> Genre.from_label() |
| status_id | Novel | status | 0->已完结->Status.FINISHED, 1->连载中->Status.ON_GOING, 2->断更->Status.DIED |
| contest | Contest | name | Find or create if non-empty |
| tags | Tag (M2M) | name | Batch find/create, link via NovelTagLink |
| banner | Banner | url | Compressed (query param only), per-novel |
| cover | Novel | cover | CDN prefix stripped |

## Key Mapping Code

```python
from database.enums import Genre, Status, PType

# Step 1: ID -> label (hardcoded, no longer depends on constants.py)
PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}

# Step 2: label -> enum (uses from_label, falls back to OTHER)
ptype = PType.from_label(PRICE_TYPE_ID_TO_LABEL.get(price_type_id, "其他"))
status = Status.from_label(STATUS_ID_TO_LABEL.get(status_id, "其他"))
genre = Genre.from_label(row["genre"])
```

DB stores enum integer values, not strings. `from_label()` returns enum members; SQLModel auto-extracts `.value` on assignment.

## Database

- **Local**: SQLite via `database/engine.py` -> `sqlite_engine`
- **Cloud**: PostgreSQL/MySQL via `.env` (DB_TYPE/HOST/PORT/USER/PASSWORD/NAME) -> `cloud_engine`
- **Table creation**: `from database.app import create_db_and_table`
- **Connection retry**: Cloud sync retries 3x with exponential backoff (2s, 4s, 8s)

```python
from database import sqlite_engine, cloud_engine
from database.app import create_db_and_table
from sqlmodel import Session

create_db_and_table(sqlite_engine)
if cloud_engine:
    create_db_and_table(cloud_engine)

with Session(sqlite_engine) as session:
    ...
    session.commit()
```

## pandas Cleaning Rules

- Deduplicate by `nid`, keep latest `last_update`
- Numeric columns: NaN -> 0, cast to int
- String columns: empty string / NaN -> None
- `author` empty -> skip row
- `cover`: strip `COVER_BASE` prefix
- `banner`: compress to query param only (reconstructible from nid)
- `tags`: non-list -> empty list `[]`
- `last_update`: parse datetime, invalid -> current time

## File Structure

```
database/         # DB/ORM module
    __init__.py    # Unified exports
    engine.py      # SQLite + cloud engine (from .env)
    models.py      # SQLModel ORM (Novel, Author, Tag, Contest, Banner)
    enums.py       # Genre/Status/PType with label <-> enum mapping
    app.py         # create_db_and_table()
ingest.py         # Data cleaning + commit_dataframe + _sync_to_cloud
main.py           # CLI entry point
output/           # CI JSONL artifacts (read-only)
```
