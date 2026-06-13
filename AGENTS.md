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

## Design Rules

- **No cold colors** (blue, indigo, sky, cyan, violet, purple, fuchsia)
- **Grid-first**: ListView uses CSS Grid, table views use `<table>`
- **Grid columns**: `grid-cols-4 md:grid-cols-6 lg:grid-cols-8`
- **Pagination**: `per_page` must be multiple of 6. Default: 24
- **Dark mode**: Always include `dark:` variants (except index header)
- **Index header**: No dark mode, no backdrop-blur

## Data Rules

- **Meta model is the standard**: `models.py` defines the canonical field names (`title`, `ptype`, `has_banner`). All datasets (JSONL), spider output, pandas processing, and dump/load pipelines MUST use these names. No renaming.
- **Died status**: `连载中` + 3 months no update → `断更`
- **A status** (pseudo): `断更` or `已完结` + (`has_banner` OR `click >= 1000w` OR `review >= 60` OR `like >= 1w` OR `praise >= 1w`) → `断更A` / `完结A`
- **Missing values**: `null`/`None` — never `0`
- **Optional fields**: All optional fields in `models.py` MUST have default value `= None`
- **Cover URL**: Stored as suffix, reconstructed via `cover_url` filter
- **Cover compression**: `to_django_dict()` strips prefix (`http://rs.sfacg.com/web/novel/images/NovelCover/Big/`), default cover → `None`

## Spider Rules

- CSS selectors/xpaths must NOT be modified
- Legacy `meta.py` must NOT be deleted — comment it out
- New code goes in `meta_batch.py` (Scrapy) or `task_runner.py` (requests)
- Max 10 pages per Scrapy run

## Testing

- **Command**: `uv run python manage.py test novels -v 2`
- **CI**: GitHub Actions runs tests on push/PR to main
- **CD**: GitHub Actions deploys SSG to GitHub Pages on push to main
