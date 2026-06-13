# Crawl & Load

## 1. Scrapy crawl (outputs CSV via pipeline)

```bash
cd /home/interset/Desktop/novel_hub/meta_spider
uv run scrapy crawl meta_batch -a num=10
```

Output: `o.csv` (Meta model field names)

## 2. Init DB (clean load)

```bash
cd /home/interset/Desktop/novel_hub/website
DB_TYPE=sqlite uv run python manage.py init_db ../meta_spider/o.csv
```

## 3. Upsert (update existing)

```bash
cd /home/interset/Desktop/novel_hub/website
DB_TYPE=sqlite uv run python manage.py upsert_dataset ../meta_spider/o.csv
```

## Notes

- Spider outputs CSV via `CSVPipeline` (field names match Meta model)
- `init_db` deletes all data first, then loads (clean initialization)
- `upsert_dataset` updates existing records, inserts new ones
- Both support `.csv` and `.jsonl` input
- `o.csv` is the default output filename
