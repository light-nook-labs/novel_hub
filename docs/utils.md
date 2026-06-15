# utils — Detailed Documentation

Detailed API documentation for the shared utilities module.

> **Quick overview**: See [utils/README.md](../utils/README.md)

## Tech Stack

- **requests** — `fetch_api` calls `Common.ashx` JSON API; `fetch_cover` fetches mobile page
- **lxml** — `fetch_html` parses detail page HTML via XPath (selectors converted from meta_spider's CSS)
- **pydantic** — `Meta` model validates scraped data, serializes to JSONL, converts to Django dict
- **pandas** — `loader` module handles DataFrame-based JSONL/CSV loading, normalization, and export
- **tqdm** — `progress()` wrapper shows progress bars for long-running operations

## Purpose

- **Scraping**: Provides `fetch_html` (lxml-based HTML parser) and `fetch_api` (requests-based JSON client) for single novel crawling. These tools reuse the same CSS selectors as meta_spider, enabling the task system to update individual novels without running the full spider.

- **Mappings**: `Mapping` class wraps Python `IntEnum` to create bidirectional label↔integer mappings. Website stores genre/status/ptype as integers for efficient queries; mappings handle conversion for display.

- **Meta**: Pydantic model that defines the canonical data format shared between meta_spider and website. `to_django_dict()` handles field renaming (nid→id), cover URL compression, and timezone normalization. `from_django_dict()` reverses the process for export.

## Config Exports

From `site_config.toml`:

| Export | Type | Description |
|--------|------|-------------|
| `TOML` | `dict` | Full config dict |
| `COVER_PREFIX` | `str` | `"https://rs.sfacg.com/web/novel/images/NovelCover/Big/"` |
| `DEFAULT_COVER` | `str` | `"defaultNew.jpg"` |
| `TIMEZONE` | `str` | `"Asia/Shanghai"` |
| `CHUNK_SIZE` | `int` | `20000` (JSONL/CSV chunk size) |

## Meta Model

Pydantic model for novel metadata. Field names match JSONL/CSV files.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nid` | `int` | Yes | Novel ID |
| `title` | `str` | Yes | Novel title |
| `author` | `str` | Yes | Author name |
| `genre` | `str` | Yes | Genre label (e.g. "magic", "eastern") |
| `status` | `str` | Yes | Status label (e.g. "on_going", "finished") |
| `ptype` | `str` | Yes | Ptype label (e.g. "free", "sign", "vip") |
| `has_banner` | `bool \| None` | No | Has promotional banner |
| `word_num` | `int \| None` | No | Word count |
| `click_num` | `int \| None` | No | Click count |
| `praise_num` | `int \| None` | No | Praise count |
| `like_num` | `int \| None` | No | Like/favorite count |
| `comment_num` | `int \| None` | No | Short comment count |
| `review_num` | `int \| None` | No | Long review count |
| `contest` | `str \| None` | No | Contest name |
| `last_update` | `datetime \| None` | No | Last update time |
| `tags` | `list[str]` | No | Tag list (default: `[]`) |
| `cover` | `str \| None` | No | Full cover URL |

### Conversion Methods

#### to_django_dict()

Converts to Django model field names and types:
- `nid` → `id`
- `author` → `author_name` (for FK lookup)
- `contest` → `contest_name` (for FK lookup)
- `genre`/`status`/`ptype` → integer enum values via mappings
- `cover` → compressed suffix (strips prefix, default cover → `None`)
- `last_update` → timezone-aware datetime (adds `Asia/Shanghai` if naive)

#### from_django_dict(data)

Creates `Meta` from Django QuerySet values:
- Expects `id` (not `nid`), `author__name` (not `author`), etc.
- Expands cover suffix to full URL by prepending `COVER_PREFIX`
- Converts integer enums back to labels via `GENRE.get_zh()`, etc.

## Mappings

`Mapping` class creates bidirectional label↔integer mappings using Python's `IntEnum`. Index 1 is always `OTHER` (fallback for unknown values).

### Mapping Class API

```python
from utils.mappings import Mapping

GENRE = Mapping(magic="magic", eastern="eastern", ...)

GENRE.get_value("magic")      # → enum int value
GENRE.get_zh(1)               # → label
GENRE.choices                 # → [(value, label), ...] for Django forms
GENRE.zh_to_value_dict()      # → {label: value} for pandas .map()
GENRE.value_to_zh_dict()      # → {value: label} for reverse conversion
GENRE.fallback()              # → OTHER enum value
```

### Pre-defined Instances

| Instance | Values |
|----------|--------|
| `GENRE` | other, magic, eastern, ancient, sci_fi, school, urban, game, doujin, mystery |
| `STATUS` | other, finished, on_going, died, active_d, active_f, removed |
| `PTYPE` | other, free, sign, vip |

## Loader Pipeline

### Loading

```python
from utils import loader

df = loader.load_jsonl("../release/dataset/")   # Single file or directory of meta_*.jsonl
df = loader.load_csv("data.csv")
```

### Normalization

```python
df = loader.normalize_df(df)
# nid → id, genre/status/ptype → int, cover → suffix, last_update → tz-aware
```

### Validation

```python
meta_list = loader.df_to_meta_list(df)   # DataFrame → list[Meta]
```

### Export

```python
df = loader.denormalize_df(django_df)    # Django field names → Pydantic names
records = loader.df_to_records(df)       # DataFrame → list[dict] (native types)
```

### Extraction

```python
loader.extract_authors(df)    # Unique author names
loader.extract_tags(df)       # Unique tags (exploded)
loader.extract_contests(df)   # Unique contest names
```

## Database Loaders

### SQLite

```python
from utils.loader_sqlite import bulk_create_ignore, bulk_create_m2m, bulk_upsert

bulk_create_ignore(Model, objects, batch_size=1000)   # INSERT OR IGNORE
bulk_create_m2m(ThroughModel, objects, batch_size=1000)  # M2M through table
bulk_upsert(Model, objects, update_fields=[...])       # update_or_create (one-by-one)
```

### PostgreSQL

```python
from utils.loader_postgres import bulk_create_ignore, bulk_create_m2m, bulk_upsert

bulk_create_ignore(Model, objects, batch_size=5000)   # ON CONFLICT DO NOTHING
bulk_create_m2m(ThroughModel, objects, batch_size=5000)  # M2M through table
bulk_upsert(Model, objects, update_fields=[...])       # ON CONFLICT DO UPDATE (raw SQL)
```

## Scraping API

### fetch_html(session, nid)

Parses detail page HTML using lxml. Returns dict:

```python
{
    "title": str,
    "author": str,
    "cover": str | None,
    "has_banner": bool,
    "tags": list[str],
    "genre": str,        # e.g. "magic", "eastern"
    "status": str,       # e.g. "on_going", "finished"
    "word_num": int,
    "click_num": int,
    "last_update": datetime,
    "praise_num": int,
    "like_num": int,
    "ptype": str,        # "free" / "sign" / "vip"
    "contest": str,
}
```

### fetch_cover(session, nid)

Gets cover URL from mobile page. Returns suffix (without prefix) or `None`.

### fetch_api(session, nid)

Gets comment/review counts. Returns:

```python
{
    "comment_num": int | None,
    "review_num": int | None,
}
```

## Logger Utilities

```python
from utils.logger import log_time, timed, progress

@log_time                    # Decorator: log execution time
def process(): ...

with timed("Loading"):       # Context manager: log block time
    ...

for item in progress(items): # tqdm wrapper with auto-logging
    ...
```
