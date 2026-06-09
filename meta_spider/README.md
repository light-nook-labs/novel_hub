# meta_spider

Scrapy spider for sfacg.com novel metadata. Batch crawls list pages → detail pages → comment API.

## Structure

```
meta_spider/
    scrapy.cfg
    meta_spider/
        __init__.py         # Re-exports Meta pydantic model
        settings.py         # Scrapy settings (UA, concurrency, throttling)
        items.py            # Unused placeholder
        middlewares.py      # Default Scrapy middlewares
        pipelines.py        # Disabled pipeline (writes tag.jsonl)
        models.py           # Pydantic Meta model
        spiders/
            __init__.py
            meta.py         # Legacy (commented out, reference only)
            meta_batch.py   # Active spider
```

## Usage

```bash
# From project root
uv run scrapy crawl meta_batch -o o.jsonl -a num=3
uv run scrapy crawl meta_batch -o o.jsonl -a begin=12465 -a num=5
```

**Always specify `-a` and `-o`. Max 10 pages per run.**

## CLI Args

| Arg | Default | Description |
|-----|---------|-------------|
| `begin` | 1 | Start page index |
| `num` | 2 | Number of pages to crawl |
| `-o` | — | Output file (JSONL) |

## Meta pydantic model

```python
class Meta(BaseModel):
    nid: int
    title: str
    author: str
    genre: str           # Chinese label
    status: str          # Chinese label
    has_banner: bool
    word_num: int | None
    click_num: int | None
    praise_num: int | None
    like_num: int | None
    score: float = 5.0
    ptype: str           # "免费" / "签约" / "VIP"
    contest: str
    last_update: datetime | None
    review_num: int | None
    comment_num: int | None
    tags: list[str]
    cover: str
```

## CSS selectors (DO NOT MODIFY)

| Page | Selector | Field |
|------|----------|-------|
| List | `.Comic_Pic_List` | item container |
| List | `.Conjunction a::attr(href)` | novel_url |
| List | `.Conjunction a img::attr(src)` | cover |
| List | `.Conjunction a img::attr(alt)` | title |
| List | `a[id*="AuthorLink"]::text` | author |
| List | `.font_red::text` | score |
| List | `.font_red ~a::text` | genre |
| Detail | `.count-detail .text-row .text::text` | stats row |
| Detail | `#BasicOperation .btn::text` | praise/like |
| Detail | `.title .tag::text` | ptype/contest |
| Detail | `.d-banner` | banner |
| Detail | `.tag-list .tag .highlight .text::text` | tags |
| API | `Common.ashx?op=getcomment` | comment_num, review_num |

## Settings

| Setting | Value |
|---------|-------|
| `USER_AGENT` | Chrome 147 |
| `ROBOTSTXT_OBEY` | True |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 2 |
| `DOWNLOAD_DELAY` | 1s |
| `TELNETCONSOLE_ENABLED` | False |
| `FEED_EXPORT_ENCODING` | utf-8 |

## Rules

- **DO NOT** modify CSS selectors/xpaths
- **DO NOT** delete `meta.py` — comment it out if changes needed
- New code goes in `meta_batch.py`
- Comment API uses async Scrapy `Request` (not `requests.Session`)
