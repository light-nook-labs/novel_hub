# utils

Shared scraping tools and data models for sfacg.com. Used by `meta_spider` and `website`.

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

## Quick Start

```python
from utils import fetch_html, fetch_cover, fetch_api, Meta

session = requests.Session()

# Single novel crawl (same selectors as meta_spider)
data = fetch_html(session, nid)     # Detail page → all fields
cover = fetch_cover(session, nid)   # Mobile page → cover suffix
comment = fetch_api(session, nid)   # Comment API → comment_num, review_num

# Validate and convert for Django ORM
meta = Meta(**data, **comment)
django_data = meta.to_django_dict()
```

## Modules

| File | Purpose |
|------|---------|
| `config.py` | Reads `site_config.toml` → exports `TOML`, `COVER_PREFIX`, `NOVEL_URL`, etc. |
| `html.py` | `fetch_html` (lxml XPath parser), `fetch_cover` (mobile page scraper) |
| `api.py` | `fetch_api` — calls `Common.ashx?op=getcomment` for comment/review counts |
| `models.py` | `Meta` Pydantic model — validates data, converts between spider and Django formats |
| `loader.py` | Pandas pipeline — `load_jsonl`, `normalize_df`, `df_to_meta_list`, `denormalize_df` |
| `loader_sqlite.py` | SQLite bulk ops — `bulk_create_ignore`, `bulk_create_m2m`, `bulk_upsert` |
| `loader_postgres.py` | PostgreSQL bulk ops — same API, uses raw SQL for `ON CONFLICT DO UPDATE` |
| `mappings.py` | `Mapping` class + `GENRE`, `STATUS`, `PTYPE` instances — bidirectional IntEnum |
| `logger.py` | `@log_time` decorator, `timed()` context manager, `progress()` tqdm wrapper |

## Module Dependencies

`utils` is standalone — no dependency on `meta_spider` or `website`.

Both `meta_spider` and `website` import from `utils`:
- `meta_spider` imports `Meta`
- `website` imports `loader`, `Meta`, `fetch_html`, `fetch_api`, `mappings`, `logger`

All three modules read `site_config.toml` directly.

## Docs

See [docs/utils.md](../docs/utils.md) for detailed API documentation.
