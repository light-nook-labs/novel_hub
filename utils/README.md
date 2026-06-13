# utils

Shared utilities for sfacg.com scraping and data processing. Used by `meta_spider` and `website`.

## Public API

```python
from utils import fetch_html, fetch_api, Meta

session = requests.Session()

# Detail page HTML → all fields
data = fetch_html(session, nid)

# Comment/review JSON API
comment = fetch_api(session, nid)
```

## Modules

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `fetch_html`, `fetch_api`, `Meta` |
| `config.py` | Reads `[scraper]` from `site_config.toml` |
| `html.py` | `fetch_html` + lxml parsing helpers |
| `api.py` | `fetch_api` (comment/review JSON) |
| `models.py` | Shared Pydantic model (`Meta`) |

## Config

Reads from `site_config.toml` (project root):

```toml
[scraper]
user_agent = "Mozilla/5.0 ..."
common_url = "https://book.sfacg.com/ajax/ashx/Common.ashx"
novel_url = "https://book.sfacg.com/Novel/{nid}/"
```

## fetch_html return value

```python
{
    "title": str,
    "author": str,
    "cover": str | None,
    "has_banner": bool,
    "tags": list[str],
    "genre": str,        # Chinese label, e.g. "魔幻"
    "status": str,       # e.g. "连载中"
    "word_num": int,
    "click_num": int,
    "last_update": datetime,
    "praise_num": int,
    "like_num": int,
    "ptype": str,        # "免费" / "签约" / "VIP"
    "contest": str,
}
```

## fetch_api return value

```python
{
    "comment_num": int | None,
    "review_num": int | None,
}
```

## CSS selectors (from meta.py, converted to XPath)

| CSS | XPath | Field |
|-----|-------|-------|
| `.count-detail .text-row .text::text` | stats row | genre, word_num, status, click_num, last_update |
| `#BasicOperation .btn::text` | buttons | praise_num, like_num |
| `.title .tag::text` | tags | ptype, contest |
| `.d-banner` | banner div | has_banner |
| `.tag-list .tag .highlight .text::text` | tag list | tags |
