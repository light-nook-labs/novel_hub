# AGENTS.md

## Project Overview

Novel Hub — Django 6.0.5 + Tailwind CSS 4.x novel metadata website from sfacg.com.

## Modules

| Module         | README                                         | Purpose                                     |
| -------------- | ---------------------------------------------- | ------------------------------------------- |
| `website/`     | [website/README.md](website/README.md)         | Django app, templates, data processing, SSG |
| `meta_spider/` | [meta_spider/README.md](meta_spider/README.md) | Scrapy spider for sfacg.com                 |
| `utils/`       | [utils/README.md](utils/README.md)             | Shared scraping client + Pydantic model     |
| `release/`     | —                                              | Release data (dataset/\*.jsonl + tasks.csv) |

## Versioning

Each iteration must update `pyproject.toml` version following semantic versioning:

- **MAJOR** (x.0.0): Breaking changes
- **MINOR** (0.x.0): New features
- **PATCH** (0.0.x): Bug fixes

**Version must match git tag.** After bumping `pyproject.toml`:

```bash
git tag v<version>
git push origin v<version>
```

## Git Workflow

- Commit code regularly
- Do not commit directly to `main`
- **Always ask for approval before `git push`**

## Package Managers

- **Python**: uv (Python 3.13)
- **Node.js**: pnpm (Tailwind CSS only)

## Key Commands

```bash
# Setup
uv sync

# Development
uv run python manage.py runserver
uv run python manage.py test novels -v 2

# Data
uv run python manage.py init_db ../release/dataset/    # Init (deletes all data first)
uv run python manage.py upsert_dataset ../release/dataset/  # Upsert (updates existing)
uv run python manage.py dump_dataset release                 # Dump DB
uv run python manage.py fix_m2m ../release/dataset/ --force  # Fix missing M2M
uv run python manage.py fill_tasks                           # Create tasks for duplicate covers
uv run python manage.py run_tasks                            # Process tasks (crawl + update)

# Static site
uv run python manage.py generate_static --output ../build --base-path novel_hub

# Tailwind
pnpm build
```

**NEVER run `uv run python manage.py test` without specifying an app.**

## Architecture

```
novel_hub/
    .env                    # Environment variables (root)
    site_config.toml        # Shared config (site, pagination, scraper)
    utils/                  # Shared scraping client + Pydantic model (see utils/README.md)
    website/                # Django project (see website/README.md)
    meta_spider/            # Scrapy spider (see meta_spider/README.md)
    release/                # Release data
    build/                  # Generated static site (gitignored)
```

## Database

- **SQLite** for development (default)
- **PostgreSQL** (Supabase) for production — uncomment in `.env`
- **Env vars**: `.env` at project root. Required: `SECRET_KEY`, `DEBUG`, `DB_TYPE`
- **⚠️ WARNING**: All PostgreSQL operations (`init_db` with PostgreSQL, etc.) MUST receive explicit user approval before execution. Never run PostgreSQL commands without asking first.

## Code Style

- **Python**: `black`, line-length 88, 4-space indent
- **HTML/JS/CSS**: 2-space indent
- **Linting**: `uv run black . && uv run flake8 .`

## Config Rules

**No hardcoded constants.** All constants MUST be managed through config files.

### Data Flow

```
site_config.toml          # Single source of truth
    ├── utils/config.py           # Reads [scraper]
    ├── website/config/settings.py  # Reads [site], [pagination]
    └── meta_spider/settings.py     # Reads [scraper]
```

### Rules

- **site_config.toml**: Site name, pagination, scraper URLs, thresholds
- **utils/config.py**: Reads `[scraper]` from TOML, exports constants
- **website/config/settings.py**: Reads `.env` for secrets, DB config; reads TOML for site/pagination
- **meta_spider/settings.py**: Reads TOML for scraper settings
- **Never** use hardcoded URLs, paths, or magic numbers in application code
- **Always** add new constants to `site_config.toml` first, then read via config module
- **No cross-dependency**: Each module reads TOML directly, not from each other

## Design Rules

- **No cold colors** (blue, indigo, sky, cyan, violet, purple, fuchsia)
- **Grid-first**: ListView uses CSS Grid, table views use `<table>`
- **Grid columns**: `grid-cols-4 md:grid-cols-6 lg:grid-cols-8`
- **Pagination**: `per_page` must be multiple of 6. Default: 24
- **Dark mode**: Always include `dark:` variants (except index header)
- **Index header**: No dark mode, no backdrop-blur

## Data Rules

- **Meta model is the standard**: `models.py` defines the canonical field names (`title`, `ptype`, `has_banner`). All datasets (JSONL), spider output, pandas processing, and dump/load pipelines MUST use these names. No renaming.
- **Died status**: `ON_GOING` + 3 months no update → `DIED`
- **A status** (pseudo): `DIED` or `FINISHED` + (`has_banner` OR `click >= 1000w` OR `review >= 60` OR `like >= 1w` OR `praise >= 1w`) → `ACTIVE_D` / `ACTIVE_F`
- **Missing values**: `null`/`None` — never `0`
- **Optional fields**: All optional fields in `models.py` MUST have default value `= None`
- **Cover URL**: Stored as suffix, reconstructed via `cover_url` filter
- **Cover compression**: `to_django_dict()` strips prefix (`http://rs.sfacg.com/web/novel/images/NovelCover/Big/`), default cover → `None`

## Task System

Task table tracks novels that need attention (duplicate covers, data issues).

### Priority Logic

| Priority | Status | Condition |
|----------|--------|-----------|
| `long_term` | `l` | Manually added high-value A-status novels (permanent) |
| `urgent` | `u` | Auto-detected: `ACTIVE_D` / `ACTIVE_F` or meets A-status criteria |
| `default` | `d` | Everything else |
| `finished` | `f` | Processed tasks (deleted after processing) |

A-status criteria: `has_banner` OR `click >= 1000w` OR `review >= 60` OR `like >= 1w` OR `praise >= 1w`

### Commands

```bash
uv run python manage.py fill_tasks              # Create tasks for duplicate covers
uv run python manage.py fill_tasks --dry-run    # Preview without creating
uv run python manage.py run_tasks               # Process tasks (crawl + update)
uv run python manage.py run_tasks --limit 100   # Process limited tasks
uv run python manage.py add_long_term <nid>     # Add novel as long-term task
```

### Workflow

1. `fill_tasks` finds novels sharing the same cover (excluding None)
2. Classifies each novel based on priority logic
3. Creates Task entries with OneToOne link to Novel
4. `run_tasks` processes tasks: crawls novel details, updates DB
5. `long_term` tasks are never deleted (permanent tracking)
6. `urgent`/`default` tasks marked as `finished` after processing

### Task Ordering

Status priority: `long_term` > `urgent` > `default` > `finished`, then `novel_id` descending.

## Snapshot System

Track novel metrics over time for trend analysis.

### Strategy

Only snapshot novels that Scrapy naturally crawls (ON_GOING list, ordered by update time):

| Source | Target | Frequency |
|--------|--------|-----------|
| Scrapy | ON_GOING (updated within 7 days) | Each crawl |
| Long-term tasks | Manually added A-status | Each crawl |
| Scheduled | Fill gaps | Daily |

### Storage

- **Supabase**: 30 days of snapshots (~6 MB)
- **GitHub**: Monthly archive (JSONL)

### Data Volume

```
ON_GOING (3,003): ~151 pages, ~1.25 hours to crawl
Updated within 7 days: ~335 novels, ~17 pages, ~8.5 minutes
Long-term tasks: ~100 novels (assumed)
Total snapshot storage: ~6 MB (30 days)
```

### Commands

```bash
uv run python manage.py smart_snapshot          # Create daily snapshots
uv run python manage.py archive_snapshots       # Archive old snapshots to JSONL
uv run python manage.py archive_snapshots --month 2026-01  # Archive specific month
```

### Workflow

1. Scrapy crawls ON_GOING list (stops at 7-day cutoff)
2. Scrapy outputs to JSONL (existing workflow)
3. `upsert_dataset` loads JSONL data into DB
4. `smart_snapshot` creates snapshots for ON_GOING novels and long-term tasks
5. `archive_snapshots` exports old data to JSONL/CSV and cleans DB

### GitHub Actions

- `daily-snapshot.yml`: Runs `smart_snapshot` daily at 04:00 Shanghai
- `monthly-archive.yml`: Runs `archive_snapshots` on 1st of each month

## Spider Rules

- CSS selectors/xpaths must NOT be modified
- Legacy `meta.py` must NOT be deleted — comment it out
- New code goes in `meta_batch.py` (Scrapy) or `task_runner.py` (requests)
- Max 10 pages per Scrapy run

## Testing

- **Command**: `uv run python manage.py test novels -v 2`
- **CI**: GitHub Actions runs tests on push/PR to main
- **CD**: GitHub Actions deploys SSG to GitHub Pages on push to main
