# Commands — Detailed Documentation

Detailed documentation for Django management commands.

> **Quick overview**: See [website/novels/management/commands/README.md](../website/novels/management/commands/README.md)

## Tech Stack

- **utils/** — loader, Meta model, fetch_html, fetch_api, logger

## Makefile

```bash
make setup              # Install dependencies (uv + pnpm)
make runserver          # Run Django dev server
make runserver PORT=8080   # Run on specific port
make makemigrations     # Create database migrations
make migrate            # Run database migrations
make createsuperuser    # Create admin user
make test               # Run novels tests
make lint               # Run black + flake8
make dev                # Watch & rebuild CSS (pnpm dev)
make build              # Build CSS minified (pnpm build)
make spider             # Crawl 10 pages (default)
make spider NUM=5       # Crawl 5 pages
make spider NUM=5 BEGIN=100   # Start at page 100
make spider NUM=5 BEGIN=100 DAYS=14  # 14-day cutoff
make init_db            # Init DB from dataset (default: ../release/dataset/)
make init_db PATH=path  # Init DB from custom path
make init_from_release URL=url  # Init from release tar archive
make upsert_dataset     # Upsert dataset (default: ../release/dataset/)
make upsert_dataset PATH=path   # Upsert from custom path
make dump_dataset       # Dump DB (default: release)
make dump_dataset PATH=path     # Dump to custom path
make create_release     # Create release tar (default: ../release.tar.gz)
make create_release OUT=file    # Create with custom output
make fix_m2m            # Fix M2M relationships
make fix_ptype          # Fix ptype (upgrade only)
make fill_tasks         # Create tasks for duplicate covers
make run_tasks          # Process tasks (default: limit 500)
make run_tasks LIMIT=100    # Process up to 100 tasks
make add_long_term NID=12345    # Add long-term task
make remove_long_term NID=12345 # Remove long-term task
make process_task_issues      # Process GitHub issues
make smart_snapshot     # Create daily snapshots
make archive_snapshots  # Archive last month snapshots
make archive_snapshots MONTH=2026-01  # Archive specific month
make generate_static    # Generate static site
make generate_static OUT=../out BASE=site WORKERS=8  # Custom output, base-path, workers
make preview            # Serve static site (default: port 8080)
make preview PORT=3000  # Serve on specific port
```

## Data Commands

### init_db

Init DB from JSONL/CSV dataset. **Deletes ALL existing data first.**

```bash
uv run python manage.py init_db ../release/dataset/
uv run python manage.py init_db ../release/dataset/meta_01.jsonl
uv run python manage.py init_db ../release/dataset/ --batch-size 5000
```

**Options:**
- `path` — Path to JSONL file, directory, or CSV file
- `--batch-size` — Batch size for bulk operations (default: 1000)

**Flow:**
1. Load and validate data through Meta model
2. Delete ALL existing data (TRUNCATE for PostgreSQL, DELETE for SQLite)
3. Create authors, tags, contests
4. Create novels with FK mappings
5. Create M2M novel-tag relationships
6. Load tasks.csv if exists

### init_from_release

Init DB from release tar archive. **Deletes ALL existing data first.**

```bash
uv run python manage.py init_from_release ../release.tar.gz
uv run python manage.py init_from_release https://github.com/.../release.tar.gz
```

**Options:**
- `archive` — Path to release.tar.gz or URL
- `--batch-size` — Batch size for bulk operations (default: 1000)
- `--skip-tasks` — Skip loading tasks.csv

**Archive format:**
```
release.tar.gz
├── jsonl/meta_*.jsonl
├── csv/meta_*.csv (optional)
└── tasks.csv (optional)
```

### upsert_dataset

Upsert dataset — updates existing records, inserts new ones.

```bash
uv run python manage.py upsert_dataset ../release/dataset/
uv run python manage.py upsert_dataset ../release/dataset/meta_01.jsonl
uv run python manage.py upsert_dataset ../release/dataset/ --skip-novels
```

**Options:**
- `path` — Path to JSONL file, directory, or CSV file
- `--batch-size` — Batch size for bulk operations (default: 1000)
- `--skip-novels` — Skip novel upsert (only update related tables)

**Flow:**
1. Load and validate data through Meta model
2. Create new authors, tags, contests (INSERT OR IGNORE)
3. Upsert novels (ON CONFLICT DO UPDATE for PostgreSQL, update_or_create for SQLite)
4. Upgrade ptype only (free → sign → VIP, never downgrade)
5. Delete and re-insert M2M relationships

### dump_dataset

Dump database to JSONL/CSV format.

```bash
uv run python manage.py dump_dataset release
uv run python manage.py dump_dataset release --format csv
uv run python manage.py dump_dataset release/dataset --format jsonl
```

**Options:**
- `output_path` — Output directory path
- `--format` — Output format: `jsonl` (default) or `csv`

**Output:**
```
release/
├── meta_01.jsonl   # 20k records each
├── meta_02.jsonl
├── ...
└── tasks.csv
```

### create_release

Create release tar archive.

```bash
uv run python manage.py create_release
uv run python manage.py create_release --output release_v1.0.tar.gz
```

**Options:**
- `--output` — Output tar file path (default: `../release.tar.gz`)

**Output:**
```
release.tar.gz
├── jsonl/meta_*.jsonl   # 20k records each
├── csv/meta_*.csv       # 20k records each
└── tasks.csv
```

### fix_m2m

Fix missing M2M tag relationships.

```bash
uv run python manage.py fix_m2m --check
uv run python manage.py fix_m2m ../release/dataset/
uv run python manage.py fix_m2m ../release/dataset/ --force
```

**Options:**
- `path` — Path to JSONL file or directory
- `--check` — Only check M2M status, do not fix
- `--force` — Skip confirmation prompt
- `--batch-size` — Batch size for bulk operations (default: 5000)

### fix_ptype

Fix ptype — upgrade only (free → sign → VIP, never downgrade).

```bash
uv run python manage.py fix_ptype ../release/dataset/
```

**Options:**
- `path` — Path to JSONL file or directory

## Task Commands

### fill_tasks

Create tasks for novels with duplicate covers.

```bash
uv run python manage.py fill_tasks
uv run python manage.py fill_tasks --dry-run
```

**Options:**
- `--dry-run` — Show results without creating tasks

**Priority logic:**
- **URGENT**: Already A-status (active_d/active_f) or meets A-status criteria (has_banner, click≥10M, review≥60, like≥10K, praise≥10K)
- **DEFAULT**: Everything else

### run_tasks

Process tasks: crawl novel details, update DB, mark finished.

```bash
uv run python manage.py run_tasks
uv run python manage.py run_tasks --limit 100
```

**Options:**
- `--limit` — Max tasks to process (default: 500)

**Flow:**
1. Get tasks ordered by status priority (long_term > urgent > default > finished)
2. For each task:
   - Crawl detail page via `fetch_html`
   - Crawl comment API via `fetch_api`
   - Build Meta object for validation
   - Update novel in DB
   - Upgrade ptype only (never downgrade)
   - Mark task as finished (except long-term)
3. Delete finished tasks

### add_long_term

Add novel as long-term task (permanent tracking).

```bash
uv run python manage.py add_long_term 12345
```

**Options:**
- `nid` — Novel ID

### remove_long_term

Remove long-term task.

```bash
uv run python manage.py remove_long_term 12345
uv run python manage.py remove_long_term --all
```

**Options:**
- `nid` — Novel ID
- `--all` — Remove all long-term tasks

### process_task_issues

Process task issues from GitHub. Reads open issues with 'task' label, extracts novel IDs, adds to Task table, closes issues.

```bash
uv run python manage.py process_task_issues
```

**Requires:** `GITHUB_TOKEN` and `GITHUB_REPO` environment variables

**Issue format:**
- Title: `[Task] 小说 ID: 123456`
- Body: `**小说 ID**: 123456`

**Flow:**
1. Fetch open issues with 'task' label from GitHub API
2. Extract novel ID from issue title or body
3. Add task to database (create novel if not exists)
4. Add comment and close issue

## Snapshot Commands

### smart_snapshot

Create daily snapshots of ON_GOING novels and long-term tasks.

```bash
uv run python manage.py smart_snapshot
```

**Flow:**
1. Get ON_GOING novels updated within `snapshot_days` (default: 7)
2. Get long-term tasks
3. Merge and deduplicate
4. Bulk create snapshots
5. Delete snapshots older than `retention_days` (default: 30)

### archive_snapshots

Archive snapshots to JSONL/CSV and delete from DB.

```bash
uv run python manage.py archive_snapshots
uv run python manage.py archive_snapshots --month 2026-01
```

**Options:**
- `--month` — Month to archive (YYYY-MM format, default: last month)

**Output:**
```
release/dataset/
├── jsonl/snapshot_2026_01.jsonl
└── csv/snapshot_2026_01.csv
```

## Static Site Commands

### generate_static

Generate static site for GitHub Pages.

```bash
uv run python manage.py generate_static --output ../build --base-path novel_hub
uv run python manage.py generate_static --workers 8
```

**Options:**
- `--output` — Output directory (default: `../build`)
- `--base-path` — Base path for URLs (e.g., 'novel_hub' for GitHub Pages)
- `--workers` — Number of worker processes (default: 4)

**Generated pages:**
- `index.html` — Homepage (1 page)
- `about/index.html` — About page (1 page)
- `authors/index.html`, `authors/page{N}.html` — Author pages (10 pages)
- `rank/index.html`, `rank/page{N}.html` — Rank pages (100 pages)
- `banners/index.html`, `banners/page{N}.html` — Banner pages (all)
- `dashboard/index.html` — Dashboard with Plotly charts (1 page)
- `comments/index.html` — Comments page (1 page)
- `404.html` — 404 page (1 page)
- `static/` — CSS, JS, images

### serve_static

Serve static site for local preview.

```bash
uv run python manage.py serve_static --port 8080
```

**Options:**
- `--dir` — Static files directory (default: `../build`)
- `--port` — Port to serve on (default: 8080)
- `--bind` — Address to bind to (default: `127.0.0.1`)
