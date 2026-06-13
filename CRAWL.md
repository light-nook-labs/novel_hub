# Crawl & Load

## 1. Scrapy crawl (outputs CSV via pipeline)

```bash
cd /home/interset/Desktop/novel_hub/meta_spider
uv run scrapy crawl meta_batch -a num=10
```

Output: `o.csv` (Meta model field names)

## 2. Load into DB

```bash
cd /home/interset/Desktop/novel_hub/website
DB_TYPE=sqlite uv run python manage.py load_dataset ../meta_spider/o.csv
```

## Notes

- Spider outputs CSV via `CSVPipeline` (field names match Meta model)
- `load_dataset` supports both `.csv` and `.jsonl` input
- `o.csv` is the default output filename
