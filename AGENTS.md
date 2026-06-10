# AGENTS.md

## Project Overview

Novel Hub — Django 6.0.5 + Tailwind CSS 4.x novel metadata website from sfacg.com. Use faker for development; real data from merged releases.

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

# Data loading (from release/)
uv run python manage.py load_jsonl ../release/dataset/meta_01.jsonl

# Dump database to release/
uv run python manage.py dump_jsonl release

# Static site generation
uv run python manage.py generate_static --output ../static_build --index-pages 10 --rank-pages 50 --base-path novel_hub
uv run python manage.py serve_static --port 8080

# Tailwind CSS
pnpm dev    # Watch mode
pnpm build  # Production build

# Run tests — ONLY test the app you modified
uv run python manage.py test novels

# Formatting & linting
uv run black .                     # Format (line-length 88, target py313)
uv run flake8 .                    # Lint
uv run pre-commit run --all-files  # Manual run all hooks
```

**NEVER run `uv run python manage.py test` without specifying an app.** Always test only the app you changed.

## Architecture

```
novel_hub/
    .env                    # Environment variables (root, not website/)
    site_config.toml        # Shared config (site, pagination, scraper)
    models.py               # Shared Pydantic model (Meta) for spider + dump
    scraper/                # requests-based HTTP client (shared by scrapy + website)
        __init__.py         # exports fetch_html, fetch_api
        config.py           # reads from site_config.toml [scraper]
        html.py             # fetch_html + lxml parsing
        api.py              # fetch_api (comment/review JSON)
    website/                # Django project root (manage.py lives here)
        config/             # Django settings, urls, wsgi
        novels/             # Main Django app
            templates/novels/
            static/novels/
            mappings.py     # GENRE/STATUS/PTYPE enum mappings
            models.py       # Novel, Author, Tag, Contest, Task
            tests.py        # 51 unit tests
        templates/          # Project-level templates (base.html, pagination)
        static/             # Project-level static files
            css/
                input.css   # Tailwind CSS input
                output.css  # Compiled Tailwind CSS
                components.css  # Reusable component styles
            js/
                main.js     # Theme toggle, search, menu, hero bg
                banners.js  # Lightbox for banner page
        manage.py
        task_runner.py      # Task table maintenance (imports scraper)
    meta_spider/            # Scrapy spider (sfacg.com scraper)
        meta_spider/spiders/
            meta.py         # Legacy (commented out, reference only)
            meta_batch.py   # Refactored batch spider
    release/                # Generated release data (gitignored)
        dataset/
            meta_01.jsonl   # 20k records each
            ...
        tasks.csv           # Task table dump
    merge/                  # Merged data from v0.0.1 + v1.1.0 (temporary)
```

## Key Facts

- **Env vars**: `.env` at project root. Required: `SECRET_KEY`, `DEBUG`, `DB_TYPE`
- **Django settings**: `website/config/settings.py` — uses `python-dotenv`, loads `.env` from project root
- **Site config**: `site_config.toml` (project root) — loaded via context processor (`config.toml.toml_config_processor`). Also holds `[scraper]` section shared by `scraper/` package.
- **Database**: SQLite default for local dev; PostgreSQL (Supabase) via env vars
- **Mappings**: `novels/mappings.py` defines `Mapping` class + `GENRE`/`STATUS`/`PTYPE` enums (en↔zh). IntEnum index 1 is always `OTHER` (fallback). Loaded as Django context processor for template use
- **Pydantic model**: `models.py` at root defines `Meta` model shared by spider and dump_jsonl

## Code Style

- **Python**: format with `black`, 4-space indentation, line-length 88
- **Templates (HTML)**: 2-space indentation
- **JavaScript**: 2-space indentation
- **CSS**: 2-space indentation

## Layout Rules

- **Grid-first**: ListView content uses CSS Grid (`grid`). Table views (`/rank`) use `<table>`. Flexbox (`flex`) only for 1D alignment (nav, pills, badges).
- **Grid columns**: `grid-cols-4 md:grid-cols-6 lg:grid-cols-8` — mobile 4 cols, desktop 6, large 8.
- **Pagination**: `per_page` must be a multiple of 6 (LCM of 4, 6, 8) so rows fill cleanly at every breakpoint. Default: 24. Exceptions: banner (12), rank (100), detail sublists (50).
- **No pagination** for tag, contest, and enum list pages — they render all items as pills/badges.
- **ListView slug**: Always use plural form (`/genres/`, `/statuses/`, `/authors/`, `/tags/`, `/contests/`).
- **Single admin user**: No authentication, no staff roles. Only one admin user via Django admin. Do not add `LoginRequiredMixin`, `UserPassesTestMixin`, or any auth-related code.

## Color Scheme

See `tailwind-component` skill for full design tokens. Key rules:
- **No cold colors** (blue, indigo, sky, cyan, violet, purple, fuchsia)
- **No pure colors** — use muted warm tones only
- **Header**: `from-amber-200 to-orange-200 dark:from-amber-900 dark:to-orange-900`
- **Index page**: No dark mode for header/hero section
- **Always include `dark:` variants** for backgrounds, text, borders, and badges (except index header)

## Dark Mode

- Dark mode is toggled by `class="dark"` on `<html>` (currently hardcoded).
- Inline styles that need dark mode use CSS custom properties: set `--var` and `--var-d` inline, override in `.dark .class { --var: var(--var-d) }`.
- **Index page header**: No dark mode (transparent over banner image).

## Template Structure

```
templates/base.html                     # Root: blocks (css, head_js, header, body, footer, body_js)
novels/templates/novels/base.html       # App: extends root, overrides header/footer/pagination/body_js
novels/templates/novels/index.html      # Page: extends app base, overrides header (hero)
novels/templates/novels/components/
    header_solid.html                   # Solid gradient header (non-index pages)
    header_solid_static.html            # Static mode solid header
    header_transparent.html             # Transparent header (index page, no dark mode)
    header_transparent_static.html      # Static mode transparent header
    header_actions.html                 # Search, theme toggle, mobile menu, GitHub
    header_actions_index.html           # Index version (no dark mode)
    header_actions_static.html          # Static mode version
    nav.html                            # Desktop navigation links
    nav_index.html                      # Index version (no dark mode)
    nav_static.html                     # Static mode version
    footer.html                         # Footer
    footer_static.html                  # Static mode footer with GitHub link
    novel_card.html                     # Novel card for grid display
    novel_row.html                      # Novel row for table display
```

## Data Rules

- **Dev data**: Use `create_fake_data` for development. Real data via `load_jsonl` from `release/dataset/`
- **Died status**: If `status == 连载中` and `last_update` is >= 3 months ago (Asia/Shanghai), treat as `died` (断更)
- **Active status**: Virtual statuses for high-engagement novels. If `died` or `finished` AND (`banner=True` OR `click_num>=10M` OR `praise_num>=10k` OR `like_num>=10k` OR `review_num>=80`), upgrade to `active_d` (断更D) or `active_f` (完结F). Real statuses: only `finished`/`on_going`
- **Missing values**: Use `null`/`None`/`NA` — never fill with `0`. `NA` marks data likely to be updated later; `0` signals finality (will never change)
- `Mapping` enums default to `OTHER` — no special handling needed for unknown labels
- **Cover URL**: Stored in DB, reconstructed in template via `cover_url` filter. Default cover used when cover is None/empty
- **Banner URL**: Pattern `http://rs.sfacg.com/web/novel/images/images/beitouNew/{nid}.jpg` — no query params, derive from `nid`
- **Novel URL**: `https://book.sfacg.com/Novel/{nid}/`
- **Title cleaning**: Strip ptype (VIP/签约) and contest name from title if appended

## Data Processing

- **Load command**: `uv run python manage.py load_jsonl <path>`
- **Dump command**: `uv run python manage.py dump_jsonl <output_dir>`
- **Scale**: ~250k novels, ~10k authors, ~500 tags, ~200 contests
- **Strategy**: pandas cleaning → Django ORM bulk insert
  - Tag/Contest: small tables (<=1000), load all into memory dict
  - Author: >10k, `bulk_create` with `ignore_conflicts=True`, then load into memory dict
  - Novel: >200k, `bulk_create` in batches of 5000
  - M2M (novel_tags): raw SQL `INSERT OR IGNORE` in batches (SQLite) or `ON CONFLICT DO NOTHING` (PostgreSQL)
- **Idempotent**: `ignore_conflicts=True` makes re-running safe
- **Dedup**: Keep latest `last_update` per `nid` when duplicates exist
- **PRAGMA**: SQLite uses `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=OFF` during bulk insert
- **Data merge**: Text/enum columns from dataset v0.0.1, numeric/cover columns from release v1.1.0

## Static Site Generation (SSG)

- **Command**: `uv run python manage.py generate_static`
- **Options**: `--output`, `--index-pages`, `--rank-pages`, `--base-path`
- **Pagination**: Uses file-based links (`page2.html`) instead of `?page=2`
- **Static mode**: Template variable `static_mode` disables interactive features
- **Deployment**: GitHub Actions workflow deploys to GitHub Pages on push to main

## Testing

- **Command**: `uv run python manage.py test novels -v 2`
- **Tests**: 51 unit tests covering views, models, mappings
- **CI**: GitHub Actions runs tests on push/PR to main

## Spider Architecture

### Components

| Component | Tech | Purpose |
|-----------|------|---------|
| `meta_spider/spiders/meta.py` | — | Legacy (commented out, reference only) |
| `meta_spider/spiders/meta_batch.py` | Scrapy | Batch crawling list + detail pages |
| `website/task_runner.py` | requests + lxml | Task table maintenance (imports scraper) |
| `website/novels/management/commands/fill_tasks.py` | Django ORM | Populate Task table with duplicate covers |

### Commands

```bash
# Batch crawl (Scrapy) — max 10 pages per run, always specify -a and -o
uv run scrapy crawl meta_batch -o o.jsonl -a num=3
uv run scrapy crawl meta_batch -o o.jsonl -a begin=12465 -a num=5

# Task maintenance (requests) — fill + process + auto-delete
uv run python website/task_runner.py
uv run python website/task_runner.py --limit 100
uv run python website/task_runner.py --nid-min 40000 --nid-max 49999 --skip-fill
uv run python website/task_runner.py --status u
```

### Rules

- CSS selectors/xpaths must NOT be modified — reuse existing selectors from meta.py
- Legacy meta.py code must NOT be deleted — comment it out
- New code goes in meta_batch.py (Scrapy) or task_runner.py (requests)
- Scrapy: batch crawling only (list pages → detail pages → comment API)
- requests: direct HTTP for Task table maintenance
- lxml: HTML parsing in task_runner.py (CSS → XPath conversion is mechanical)

## Task Model

- **Purpose**: CI-triggered requests spider to re-scrape novels with data issues
- **Schema**: `id` (auto), `novel_id` (FK UNIQUE to Novel), `status` (CharField, choices: `u`=urgent, `d`=default, `f`=finished)
- **Population**: `uv run python manage.py fill_tasks` — finds novels with duplicate cover URLs
- **Duplicate covers**: Spider bug causes some novels to share the same cover URL. These are inserted into Task with `status="d"` ordered by `last_update` DESC
- **Processing**: task_runner marks finished tasks as `f`, then batch deletes them at the end
- **Missing data**: Spider bug also causes missing `comment_num` and `review_num` — do NOT fix or fill into Task
- **Test data**: `list.csv` — banner novels by 10k interval (gitignored, do not delete)
- **GitHub issues**: See open issues for spider bug details
