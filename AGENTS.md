# AGENTS.md

## Project Overview

Novel Hub — Django 6.0.5 + Tailwind CSS 4.x novel metadata website from sfacg.com.

## Modules

| Module | README | Purpose |
|--------|--------|---------|
| `website/` | [website/README.md](website/README.md) | Django app, templates, data processing, SSG |
| `meta_spider/` | [meta_spider/README.md](meta_spider/README.md) | Scrapy spider for sfacg.com |
| `scraper/` | [scraper/README.md](scraper/README.md) | requests-based HTTP client |
| `release/` | — | Release data (dataset/*.jsonl + tasks.csv) |

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
uv run python manage.py load_jsonl ../release/dataset/    # Load all
uv run python manage.py dump_jsonl release                 # Dump DB
uv run python manage.py reset_psql --limit 100             # Reset PostgreSQL

# Static site
uv run python manage.py generate_static --output ../static_build --index-pages 10 --rank-pages 50 --base-path novel_hub

# Tailwind
pnpm build
```

**NEVER run `uv run python manage.py test` without specifying an app.**

## Architecture

```
novel_hub/
    .env                    # Environment variables (root)
    site_config.toml        # Shared config (site, pagination, scraper)
    models.py               # Shared Pydantic model (Meta)
    website/                # Django project (see website/README.md)
    meta_spider/            # Scrapy spider (see meta_spider/README.md)
    scraper/                # HTTP client (see scraper/README.md)
    release/                # Release data
    static_build/           # Generated static site (gitignored)
```

## Database

- **SQLite** for development (default)
- **PostgreSQL** (Supabase) for production — uncomment in `.env`
- **Env vars**: `.env` at project root. Required: `SECRET_KEY`, `DEBUG`, `DB_TYPE`

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

- **Died status**: `连载中` + 3 months no update → `断更`
- **Active status**: High-engagement upgrade to `断更D` / `完结F`
- **Missing values**: `null`/`None` — never `0`
- **Cover URL**: Stored as suffix, reconstructed via `cover_url` filter

## Spider Rules

- CSS selectors/xpaths must NOT be modified
- Legacy `meta.py` must NOT be deleted — comment it out
- New code goes in `meta_batch.py` (Scrapy) or `task_runner.py` (requests)
- Max 10 pages per Scrapy run

## Testing

- **Command**: `uv run python manage.py test novels -v 2`
- **CI**: GitHub Actions runs tests on push/PR to main
- **CD**: GitHub Actions deploys SSG to GitHub Pages on push to main
