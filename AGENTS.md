# AGENTS.md

## Project Overview

Novel Hub — Django 6.0.5 + Tailwind CSS 4.x + HTMX novel metadata website from sfacg.com. Use faker for development; real data processing (scrapy + pandas) happens after website development is complete.

## Versioning

Each iteration must update `pyproject.toml` version following semantic versioning:

- **MAJOR** (x.0.0): Breaking changes — database schema changes, incompatible API changes, major feature rewrites
- **MINOR** (0.x.0): New features — new views, new templates, new models, new apps, backward-compatible additions
- **PATCH** (0.0.x): Bug fixes — typo fixes, style tweaks, test fixes, documentation updates, dependency patch updates

**Version must match git tag.** After bumping `pyproject.toml`, create a matching tag:
```bash
git tag v<version>  # e.g. git tag v2.1.2
git push origin v<version>
```

## Git Workflow

- Commit code regularly
- Each task in the task list should have at least one commit
- Do not commit directly to `main`
- **Always ask for approval before `git push`** — never push without user confirmation

## Package Managers

- **Python**: uv (Python 3.13)
- **Node.js**: pnpm (Tailwind CSS only)

## Commands

```bash
# Setup
uv sync                                    # Install Python deps
uv run pre-commit install                  # One-time: install git hooks

# Django
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py shell

# Fake data (for development)
uv run python manage.py create_fake_data -n 1000

# Real data loading (after website development)
gh release download --repo <owner>/<repo>  # Download dataset from release
uv run python manage.py load_jsonl ../dataset/data

# Tailwind CSS
pnpm dev    # Watch mode
pnpm build  # Production build

# Run tests — ONLY test the app you modified
uv run python manage.py test <app_name>

# Scrapy spider — avoid running during dev; if needed, always specify -a and -o
# NEVER run without arguments. Max 10 pages per run.
uv run scrapy crawl meta -o o.jsonl -a num=3
uv run scrapy crawl meta -o o.jsonl -a begin=12465 -a num=5

# Formatting & linting
uv run black .                     # Format (line-length 88, target py313)
uv run flake8 .                    # Lint
uv run pre-commit run --all-files  # Manual run all hooks
```

**NEVER run `uv run python manage.py test` without specifying an app.** Always test only the app you changed.

## Architecture

```
novel_hub/
    website/                # Django project root (manage.py lives here)
        config/             # Django settings, urls, wsgi
        novels/             # Main Django app
            templates/novels/
            static/novels/
            mappings.py     # GENRE/STATUS/PTYPE enum mappings
            models.py       # Novel, Author, Tag, Contest
        templates/          # Project-level templates (base.html)
        static/             # Project-level static files
        manage.py
        site_config.toml    # Site settings (loaded via context processor)
    meta_spider/            # Scrapy spider (sfacg.com scraper) — minimal changes
    dataset/                # >100MB, gitignored (real data, for later use)
```

Reference project: `Desktop/learner` — follow its Django + Tailwind + HTMX patterns.

## Key Facts

- **Env vars**: Copy `.sample.env` → `.env` to `website/`. Required: `SECRET_KEY`, `DEBUG`
- **Django settings**: `website/config/settings.py` — uses `python-dotenv`, loads `.env` from `website/`
- **Site config**: `website/site_config.toml` — loaded via context processor (`config.toml.toml_config_processor`)
- **Database**: SQLite default for local dev; MySQL/PostgreSQL via env vars
- **Mappings**: `novels/mappings.py` defines `Mapping` class + `GENRE`/`STATUS`/`PTYPE` enums (en↔zh). IntEnum index 1 is always `OTHER` (fallback). Loaded as Django context processor for template use
- **CI workflow** (`.github/workflows/auto-14.yml`): Manual dispatch, runs scrapy spider, commits output to `output/meta_DD.jsonl`
- **BEGIN.txt**: Tracks spider pagination state across CI runs
- **Supabase skills** installed via `skills-lock.json` — Supabase Postgres best practices apply

## Code Style

- **Python**: format with `black`, 4-space indentation, line-length 88
- **Templates (HTML)**: 2-space indentation
- **JavaScript**: 2-space indentation
- **CSS**: 2-space indentation

## Data Rules

- **Dev data**: Use `create_fake_data` for development. Real data via `load_jsonl` after website is complete
- **Died status**: If `status == 连载中` and `last_update` is >= 3 months ago (Asia/Shanghai), treat as `died` (断更)
- **Missing values**: Use `null`/`None`/`NA` — never fill with `0`. `NA` marks data likely to be updated later; `0` signals finality (will never change)
- `Mapping` enums default to `OTHER` — no special handling needed for unknown labels
- **Cover URL**: Common prefix `http://rs.sfacg.com/web/novel/images/NovelCover/Big/` — store only the suffix in DB, reconstruct full URL in template
- **Banner URL**: Pattern `http://rs.sfacg.com/web/novel/images/images/beitouNew/{nid}.jpg` — no query params, derive from `nid`
- **Novel URL**: `https://book.sfacg.com/Novel/{nid}/`
