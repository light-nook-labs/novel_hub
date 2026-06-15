# meta_spider

Scrapy spider for sfacg.com novel metadata. Batch crawls list pages → detail pages → comment API, outputting validated `Meta` objects to JSONL.

## Tech Stack

- **Scrapy** — async web crawling framework; spider yields `Meta` objects serialized to JSONL via `-o` flag
- **utils/models.py** — imports `Meta` Pydantic model for data validation

## Purpose

Batch crawl sfacg.com novel list pages to extract metadata for all novels. Each novel goes through three stages: list page (basic info), detail page (metrics), and comment API (review counts). A cutoff mechanism stops crawling when novels haven't been updated within N days, enabling efficient incremental updates.

## Quick Start

```bash
# Crawl 10 pages
uv run scrapy crawl meta_batch -o o.jsonl -a num=10

# Crawl from page 100, 5 pages, 14-day cutoff
uv run scrapy crawl meta_batch -o o.jsonl -a begin=100 -a num=5 -a days=14
```

## Modules

```
meta_spider/
├── scrapy.cfg
└── meta_spider/
    ├── settings.py         # Reads site_config.toml → USER_AGENT, URLs
    ├── pipelines.py        # CSVPipeline writes Meta items to o.csv
    ├── models.py           # Re-exports Meta from utils.models
    └── spiders/
        ├── meta.py         # Legacy (commented out, reference only)
        └── meta_batch.py   # Active spider — MetaBatchSpider
```

## CLI Args

| Arg | Default | Description |
|-----|---------|-------------|
| `begin` | 1 | Start page index |
| `num` | 2 | Number of pages |
| `days` | 7 | Cutoff days — stop if novel updated before this |
| `-o` | — | Output file (JSONL) |

## Module Dependencies

- Imports `Meta` from `utils.models`
- Reads `site_config.toml` via `settings.py`

## Docs

See [docs/meta_spider.md](../docs/meta_spider.md) for CSS selectors, parsing methods, and detailed documentation.
