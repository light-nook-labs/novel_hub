# website

Django project root for Novel Hub. Contains the main web application, data processing commands, and static site generation.

## Structure

```
website/
    manage.py
    config/                 # Django settings, urls, wsgi
        settings.py         # Loads .env from project root
    novels/                 # Main Django app
        models.py           # Novel, Author, Tag, Contest, Task
        views.py            # ListView, DetailView for all pages
        mappings.py         # GENRE/STATUS/PTYPE enum mappings
        tests.py            # 51 unit tests
        templatetags/
            novel_tags.py   # cover_url, humanize_num, pill_bg, etc.
        management/
            commands/
                create_fake_data.py
                load_jsonl.py       # Load JSONL → DB (psql/sqlite optimized)
                load_tasks.py       # Load tasks.csv separately
                dump_jsonl.py       # Dump DB → JSONL
                generate_static.py  # SSG for GitHub Pages
                serve_static.py     # Local preview server
                fill_tasks.py       # Populate Task table
                reset_psql.py       # Clear + reload PostgreSQL
        templates/novels/
            base.html
            index.html
            rank.html
            detail.html
            banners.html
            ...
            components/
                header_solid.html
                header_transparent.html
                nav.html
                footer.html
                novel_card.html
                novel_row.html
                ...
    templates/              # Project-level templates
        base.html           # Root: blocks (css, head_js, header, body, footer)
    static/
        css/
            input.css       # Tailwind CSS input
            output.css      # Compiled CSS
            components.css  # Reusable component styles
        js/
            main.js         # Theme toggle, search, menu, hero bg
            banners.js      # Lightbox for banner page
    task_runner.py          # Task table maintenance (imports scraper)
```

## Commands

```bash
# Development
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py shell

# Fake data
uv run python manage.py create_fake_data -n 1000

# Data loading
uv run python manage.py load_jsonl ../release/dataset/meta_01.jsonl    # Single file
uv run python manage.py load_jsonl ../release/dataset/                 # All files + tasks.csv
uv run python manage.py load_tasks                                     # Tasks only

# Data dump
uv run python manage.py dump_jsonl release

# PostgreSQL
uv run python manage.py reset_psql --limit 100

# Static site
uv run python manage.py generate_static --output ../static_build --index-pages 10 --rank-pages 50 --base-path novel_hub
uv run python manage.py serve_static --port 8080

# Testing
uv run python manage.py test novels -v 2

# Tailwind CSS
pnpm dev      # Watch mode
pnpm build    # Production build
```

## Data Processing

- **Scale**: ~250k novels, ~10k authors, ~500 tags, ~200 contests
- **Strategy**: pandas cleaning → Django ORM bulk insert
- **Idempotent**: `ignore_conflicts=True` makes re-running safe
- **Dedup**: Keep latest `last_update` per `nid`
- **Database-specific**: PostgreSQL uses `execute_values` for bulk ops; SQLite uses PRAGMA tuning

### load_jsonl

- Reads cover prefix from `site_config.toml` (not hardcoded)
- Strips URL prefix to save DB space
- Converts `nan` strings to `NULL`
- Timestamps in milliseconds (`unit='ms'`)
- Auto-loads `tasks.csv` when loading from directory

## Data Rules

- **Died status**: `status == 连载中` + `last_update` >= 3 months ago → `died`
- **Active status**: High-engagement novels upgrade to `active_d` / `active_f`
- **Missing values**: `null`/`None` — never fill with `0`
- **Cover URL**: Stored as suffix, reconstructed via `cover_url` template filter

## Template Structure

- `header_solid.html` — Gradient header (non-index pages)
- `header_transparent.html` — Transparent header (index, no dark mode)
- `nav.html` / `nav_index.html` / `nav_static.html` — Navigation variants
- `header_actions*.html` — Search, theme toggle, menu, GitHub
- `novel_card.html` — Grid card
- `novel_row.html` — Table row with tags below badges

## Static Site Generation

- File-based pagination (`page2.html` instead of `?page=2`)
- `static_mode` template variable disables interactive features
- GitHub Actions deploys to GitHub Pages on push to main
