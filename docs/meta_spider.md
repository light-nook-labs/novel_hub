# meta_spider — Detailed Documentation

Detailed documentation for the Scrapy spider.

> **Quick overview**: See [meta_spider/README.md](../meta_spider/README.md)

## Tech Stack

- **Scrapy** — async web crawling framework; spider yields `Meta` objects serialized to JSONL via `-o` flag
- **utils/models.py** — imports `Meta` Pydantic model for data validation

## Purpose

Batch crawl sfacg.com novel list pages to extract metadata for all novels. Each novel goes through three stages: list page (basic info), detail page (metrics), and comment API (review counts). A cutoff mechanism stops crawling when novels haven't been updated within N days, enabling efficient incremental updates.

## Crawling Flow

```
List page (PageIndex=N)
  └─ for each .Comic_Pic_List item:
       ├─ Extract: nid, title, author, genre, cover
       └─ yield Request → Detail page
            └─ parse_detail()
                 ├─ Extract: word_num, status, click_num, last_update,
                 │           praise_num, like_num, ptype, contest,
                 │           has_banner, tags
                 ├─ Check cutoff: last_update < now - days → stop
                 └─ yield Request → Comment API
                      └─ parse_comment()
                           └─ yield Meta(**data, comment_num, review_num)
```

## CSS Selectors (DO NOT MODIFY)

### List Page

| Selector | Field |
|----------|-------|
| `.Comic_Pic_List` | Item container |
| `.Conjunction a::attr(href)` | novel_url |
| `.Conjunction a img::attr(src)` | cover |
| `.Conjunction a img::attr(alt)` | title |
| `a[id*="AuthorLink"]::text` | author |
| `.font_red ~a::text` | genre |

### Detail Page

| Selector | Field |
|----------|-------|
| `.count-detail .text-row .text::text` | Stats row |
| `#BasicOperation .btn::text` | Praise/like buttons |
| `.title .tag::text` | Ptype/contest tags |
| `.d-banner` | Banner presence |
| `.tag-list .tag .highlight .text::text` | Tags |

### Comment API

`Common.ashx?op=getcomment&nid={nid}` → JSON with `ShortCommentNum`, `LongCommentNum`

## Parsing Methods

### _row(row)

Input: `['类型：魔幻', '字数：3240533字[连载中]', '人气：4757.4万', '更新：2026/5/25 20:26:36']`

Output: `{"genre": "魔幻", "word_num": 3240533, "status": "连载中", "click_num": 47574000, "last_update": datetime(...)}`

### _btns(btns)

Input: `['点击阅读', '赞 27872', '收藏 278629']`

Output: `{"praise_num": 27872, "like_num": 278629}`

### _ptype_contest(ptype_contest)

Input: `['VIP', '第九届冬季征文']`

Output: `{"ptype": "VIP", "contest": "第九届冬季征文"}`

## Settings

Reads from `site_config.toml` via `settings.py`:

| Setting | Source | Default |
|---------|--------|---------|
| `USER_AGENT` | `urls.user_agent` | Scrapy default |
| `ROBOTSTXT_OBEY` | — | `True` |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | — | `2` |
| `DOWNLOAD_DELAY` | — | `1s` |

## Rules

1. DO NOT modify CSS selectors/xpaths
2. DO NOT delete `meta.py` — comment it out
3. New code goes in `meta_batch.py`
4. Max 10 pages per run
