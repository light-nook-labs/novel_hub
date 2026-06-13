# Management Commands

All commands run from `website/` directory:

```bash
cd website && uv run python manage.py <command>
```

## Quick Reference

| Command | Purpose | DB |
|---------|---------|-----|
| `init_db` | Initialize DB from release JSONL (auto-detect) | both |
| `load_dataset` | Update DB from CSV/JSONL file (auto-detect) | both |
| `dump_dataset` | Export DB to JSONL + CSV | both |
| `create_release` | Create release/ with JSONL + CSV + tasks | both |
| `load_psql` | Update PostgreSQL from CSV/JSONL file | psql |
| `load_sqlite` | Update SQLite from CSV/JSONL file | sqlite |
| `reset_psql` | TRUNCATE all PostgreSQL tables | psql |

---

## Data Pipeline

### First-time setup

```bash
# SQLite (dev)
uv run python manage.py migrate
uv run python manage.py init_db --path ../release/dataset

# PostgreSQL (prod)
uv run python manage.py migrate
uv run python manage.py init_psql --path ../release/dataset
```

### Incremental update

```bash
# Auto-detect DB type
uv run python manage.py load_dataset ../release/dataset/

# Or specify directly
uv run python manage.py load_psql ../release/dataset/ --force
uv run python manage.py load_sqlite ../release/dataset/ --force
```

### Export

```bash
uv run python manage.py dump_dataset release
```

---

## Command Details

### `init_db`

Initialize database from release dataset. Auto-detects DB type and delegates to `init_psql` or `init_sqlite`.

```bash
uv run python manage.py init_db
uv run python manage.py init_db --path ../release/dataset --limit 1000
```

### `init_psql`

PostgreSQL-only initialization. Uses COPY for bulk load, drops/rebuilds indexes and FK constraints around insert, runs ANALYZE after.

```bash
uv run python manage.py init_psql
uv run python manage.py init_psql --limit 1000
```

### `init_sqlite`

SQLite-only initialization. Uses ORM bulk_create with WAL mode and optimized PRAGMAs.

```bash
uv run python manage.py init_sqlite
uv run python manage.py init_sqlite --limit 1000
```

### `load_dataset`

Update database from a dataset file (INSERT + UPDATE). Auto-detects DB type. File only — no directories.

```bash
uv run python manage.py load_dataset /tmp/spider_data.jsonl
uv run python manage.py load_dataset /tmp/spider_data.jsonl --limit 1000
uv run python manage.py load_dataset /tmp/spider_data.jsonl --force
```

### `load_psql`

PostgreSQL-only update. Uses COPY into temp table for upserts (3x faster than execute_values). File only.

```bash
uv run python manage.py load_psql /tmp/spider_data.jsonl
uv run python manage.py load_psql /tmp/spider_data.jsonl --force
```

### `load_sqlite`

SQLite-only update. Uses ORM with WAL mode. File only.

```bash
uv run python manage.py load_sqlite /tmp/spider_data.jsonl
uv run python manage.py load_sqlite /tmp/spider_data.jsonl --force
```

### `reset_psql`

TRUNCATE all tables in PostgreSQL. Requires confirmation.

```bash
uv run python manage.py reset_psql
```

### `create_fake_data`

Generate fake novel data for development.

```bash
uv run python manage.py create_fake_data           # 500 novels
uv run python manage.py create_fake_data -n 1000   # 1000 novels
```

### `fill_tasks`

Find novels with duplicate cover URLs and populate Task table.

```bash
uv run python manage.py fill_tasks
```

### `run_tasks`

Fill tasks and re-scrape each novel from sfacg.com.

```bash
uv run python manage.py run_tasks                    # fill + scrape all
uv run python manage.py run_tasks --limit 100        # limit to 100
uv run python manage.py run_tasks --skip-fill         # skip fill, scrape existing
uv run python manage.py run_tasks --status u          # urgent only
uv run python manage.py run_tasks --nid-min 1000 --nid-max 2000  # ID range
```

### `dump_dataset`

Export database to release/ (jsonl/ + csv/ + tasks.csv).

```bash
uv run python manage.py dump_dataset
uv run python manage.py dump_dataset --output ../release
```

### `create_release`

Create release tar.gz from dump_dataset output.

```bash
uv run python manage.py create_release
uv run python manage.py create_release --tag v20260613
```

### `load_tasks`

Load tasks.csv into Task table.

```bash
uv run python manage.py load_tasks ../release/tasks.csv --force
```

### `strip_cover_prefix`

Remove cover URL prefix, keep suffix only.

```bash
uv run python manage.py strip_cover_prefix
```

### `generate_static`

Generate static HTML for GitHub Pages.

```bash
uv run python manage.py generate_static --output ../build
uv run python manage.py generate_static --output ../build --base-path novel_hub  # for GH Pages
uv run python manage.py generate_static --index-pages 2 --rank-pages 50
```

Options:
- `--output` — Output directory (default: build)
- `--base-path` — URL prefix for subdirectory deploy (e.g. `novel_hub` for GH Pages)
- `--index-pages` — Number of index pages (default: 1)
- `--rank-pages` — Number of rank pages (default: 100)
- `--authors-pages` — Number of author pages (default: 10)
- `--workers` — Parallel render workers (default: 32)

### `serve_static`

Preview static site locally. Default port: 3000.

```bash
uv run python manage.py serve_static
uv run python manage.py serve_static --port 8080
uv run python manage.py serve_static --dir ../build --base-path novel_hub  # test GH Pages routing
```

---

## Makefile Shortcuts

```bash
make dev              # Run dev server
make static           # Generate static site
make serve            # Preview static site
make test             # Run tests
make lint             # Black + flake8
make clean            # Remove build/ and db.sqlite3
make tailwind         # Tailwind dev mode
make tailwind-build   # Tailwind production build
```

---

## Utils

Shared utilities in `novels/management/utils/`:

| File | Purpose |
|------|---------|
| `__init__.py` | Column definitions, mapping helpers, config readers |
| `pandas_utils.py` | JSONL parsing, entity extraction, DataFrame operations |
| `psql_utils.py` | COPY, upsert, index/constraint management, session tuning |
| `sqlite_utils.py` | WAL mode, ORM bulk_create, PRAGMA optimize |
| `tasks_utils.py` | Shared task CSV loading |
| `logging.py` | `@log_timing` decorator for step-level timing |
