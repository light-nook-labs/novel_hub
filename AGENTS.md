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

## Key Facts

- **Env vars**: Copy `.sample.env` → `.env` to `website/`. Required: `SECRET_KEY`, `DEBUG`
- **Django settings**: `website/config/settings.py` — uses `python-dotenv`, loads `.env` from `website/`
- **Site config**: `website/site_config.toml` — loaded via context processor (`config.toml.toml_config_processor`)
- **Database**: SQLite default for local dev; MySQL/PostgreSQL via env vars
- **Mappings**: `novels/mappings.py` defines `Mapping` class + `GENRE`/`STATUS`/`PTYPE` enums (en↔zh). IntEnum index 1 is always `OTHER` (fallback). Loaded as Django context processor for template use
- **Supabase skills** installed via `skills-lock.json` — Supabase Postgres best practices apply

## Code Style

- **Python**: format with `black`, 4-space indentation, line-length 88
- **Templates (HTML)**: 2-space indentation
- **JavaScript**: 2-space indentation
- **CSS**: 2-space indentation

## Layout Rules

- **Grid-first**: ListView content uses CSS Grid (`grid`). Table views (`/rank`) use `<table>`. Flexbox (`flex`) only for 1D alignment (nav, pills, badges).
- **Grid columns**: `grid-cols-4 md:grid-cols-6 lg:grid-cols-8` — mobile 4 cols, desktop 6, large 8.
- **Pagination**: `per_page` must be a multiple of 6 (LCM of 4, 6, 8) so rows fill cleanly at every breakpoint. Default: 24. Exceptions: banner (12), rank (100), detail sublists (50).
- **No pagination** for tag and contest list pages — they render all items as pills.
- **Single admin user**: No authentication, no staff roles. Only one admin user via Django admin. Do not add `LoginRequiredMixin`, `UserPassesTestMixin`, or any auth-related code.

## Color Scheme

### Primary Palette
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Header gradient | Amber-200 → Orange-200 | Amber-900 → Orange-900 | `from-amber-200 to-orange-200 dark:from-amber-900 dark:to-orange-900` |
| Accent / hover | Amber-700 | Amber-300 | `hover:text-amber-700 dark:hover:text-amber-300` |
| Active filter | Gray-200 | Gray-700 | `bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200` |

### Surface & Background
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Page bg | Gray-50 | Gray-900 | `bg-gray-50 dark:bg-gray-900` |
| Card / surface | White | Gray-800 | `bg-white dark:bg-gray-800` |
| Border | Gray-200 | Gray-700 | `border-gray-200 dark:border-gray-700` |

### Text
| Role | Light | Dark | Tailwind |
|------|-------|------|----------|
| Primary | Gray-800 | Gray-100 | `text-gray-800 dark:text-gray-100` |
| Secondary | Gray-600 | Gray-400 | `text-gray-600 dark:text-gray-400` |
| Muted | Gray-400 | Gray-500 | `text-gray-400 dark:text-gray-500` |

### Status Badges
| Status | Light | Dark | Tailwind |
|--------|-------|------|----------|
| Finished (已完结) | Green-100/700 | Green-900/300 | `bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300` |
| Ongoing (连载中) | Red-100/700 | Red-900/300 | `bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300` |
| Died (断更) | Gray-100/700 | Gray-700/300 | `bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300` |
| Other | Gray-100/700 | Gray-700/300 | same as died |

### Category Badges
| Category | Light | Dark | Tailwind |
|----------|-------|------|----------|
| Genre | Orange-100/700 | Orange-900/300 | `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300` |
| Type (ptype) | Rose-100/700 | Rose-900/300 | `bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300` |
| Contest | Orange-100/700 | Orange-900/300 | `bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300` |
| Tag / Contest pills | Deterministic HSL from `hash("{model}_{id}")` | same with dark overrides | Inline CSS custom properties |

### Interactive
| Element | Light | Dark | Tailwind |
|---------|-------|------|----------|
| Link hover | Amber-600 | Amber-400 | `hover:text-amber-600 dark:hover:text-amber-400` |
| Card hover shadow | shadow-md | shadow-md | `hover:shadow-md` |
| Button primary | Amber-600 | Amber-500 | `bg-amber-600 dark:bg-amber-500` |

## Dark Mode

- Always include `dark:` variants for backgrounds, text, borders, and badges.
- Dark mode is toggled by `class="dark"` on `<html>` (currently hardcoded).
- Inline styles that need dark mode use CSS custom properties: set `--var` and `--var-d` inline, override in `.dark .class { --var: var(--var-d) }`.

## Data Rules

- **Dev data**: Use `create_fake_data` for development. Real data via `load_jsonl` after website is complete
- **Died status**: If `status == 连载中` and `last_update` is >= 3 months ago (Asia/Shanghai), treat as `died` (断更)
- **Missing values**: Use `null`/`None`/`NA` — never fill with `0`. `NA` marks data likely to be updated later; `0` signals finality (will never change)
- `Mapping` enums default to `OTHER` — no special handling needed for unknown labels
- **Cover URL**: Common prefix `http://rs.sfacg.com/web/novel/images/NovelCover/Big/` — store only the suffix in DB, reconstruct full URL in template. URLs containing `defaultNew.jpg` are default covers — store as `None`
- **Banner URL**: Pattern `http://rs.sfacg.com/web/novel/images/images/beitouNew/{nid}.jpg` — no query params, derive from `nid`
- **Novel URL**: `https://book.sfacg.com/Novel/{nid}/`

## Data Processing

- **Command**: `uv run python manage.py load_jsonl` (default: `dataset/data/`)
- **Scale**: ~250k novels, ~10k authors, ~500 tags, ~200 contests
- **Strategy**: pandas cleaning → Django ORM bulk insert
  - Tag/Contest: small tables (<=1000), load all into memory dict
  - Author: >10k, `bulk_create` with `ignore_conflicts=True`, then load into memory dict
  - Novel: >200k, `bulk_create` in batches of 5000
  - M2M (novel_tags): raw SQL `INSERT OR IGNORE` in batches
- **Idempotent**: `ignore_conflicts=True` makes re-running safe
- **Dedup**: Keep latest `last_update` per `nid` when duplicates exist
- **PRAGMA**: SQLite uses `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=OFF` during bulk insert
