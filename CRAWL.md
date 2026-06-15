# Crawl & Load

## 1. Scrapy crawl

```bash
cd /home/interset/Desktop/novel_hub/meta_spider

# Basic: crawl 3 pages from page 1
uv run scrapy crawl meta_batch -o o.jsonl -a num=3

# From specific page
uv run scrapy crawl meta_batch -o o.jsonl -a begin=80 -a num=20

# With 7-day cutoff (stop when novel older than 7 days)
uv run scrapy crawl meta_batch -o o.jsonl -a begin=80 -a num=20 -a days=7
```

Output: `o.jsonl` (Meta model field names)

## 2. Upsert (update existing)

```bash
cd /home/interset/Desktop/novel_hub/website
uv run python manage.py upsert_dataset ../meta_spider/o.jsonl
```

## 3. Create snapshots

```bash
cd /home/interset/Desktop/novel_hub/website
uv run python manage.py smart_snapshot
```

Creates daily snapshots for:
- ON_GOING novels updated within 7 days
- Long-term tasks

## 4. Archive snapshots

```bash
# Archive last month
uv run python manage.py archive_snapshots

# Archive specific month
uv run python manage.py archive_snapshots --month 2026-06
```

Exports to `release/dataset/jsonl/snapshot_YYYY_MM.jsonl` and CSV.

## Full Workflow Example

```bash
# 1. Crawl from page 80 (where June 7 data is), 7-day cutoff
cd meta_spider
uv run scrapy crawl meta_batch -o /tmp/june7.jsonl -a begin=80 -a num=20 -a days=7

# 2. Load into database
cd website
uv run python manage.py upsert_dataset /tmp/june7.jsonl

# 3. Create snapshots
uv run python manage.py smart_snapshot

# 4. Add long-term tracking for important novel
uv run python manage.py add_long_term 763391
```

## Notes

- `upsert_dataset` updates existing records, inserts new ones
- `smart_snapshot` deletes snapshots older than 30 days
- `archive_snapshots` exports to JSONL/CSV and deletes from DB
- Scrapy `days` arg controls cutoff (default: 7)
