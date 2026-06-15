# website

Django project root for Novel Hub. Contains the main web application, data processing commands, and static site generation.

## Structure

```
website/
    manage.py
    config/                 # Django settings, urls, wsgi
        settings.py         # Loads .env from project root
    novels/                 # Main Django app
        models.py           # Novel, Author, Tag, Contest, Task, NovelSnapshot
        views.py            # ListView, DetailView for all pages
        mappings.py         # GENRE/STATUS/PTYPE enum mappings
        tests/              # 118 unit tests
            test_models.py
            test_views.py
            test_tags.py
            test_commands.py
            test_search.py
            test_pagination.py
        templatetags/
            novel_tags.py   # cover_url, humanize_num, pill_bg, etc.
        management/
            commands/
                init_db.py              # Init DB (deletes all data first)
                upsert_dataset.py       # Upsert (updates existing records)
                dump_dataset.py         # Dump DB → JSONL/CSV
                fix_m2m.py              # Fix missing M2M tag relationships
                generate_static.py      # SSG for GitHub Pages
                serve_static.py         # Local preview server
                fill_tasks.py           # Create tasks for duplicate covers
                run_tasks.py            # Process tasks (crawl + update)
                add_long_term.py        # Add novel as long-term task
                remove_long_term.py     # Remove long-term task
                smart_snapshot.py       # Create daily snapshots
                archive_snapshots.py    # Archive snapshots to JSONL/CSV
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
    task_runner.py          # Task table maintenance (imports utils)
```

## Commands

```bash
# Development
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py shell

# Data init (deletes all data first)
uv run python manage.py init_db ../release/dataset/                 # All files + tasks.csv
uv run python manage.py init_db ../release/dataset/meta_01.jsonl    # Single file

# Data upsert (updates existing)
uv run python manage.py upsert_dataset ../release/dataset/

# Data dump
uv run python manage.py dump_dataset release

# Fix M2M relationships
uv run python manage.py fix_m2m --check                    # Check M2M status
uv run python manage.py fix_m2m ../release/dataset/ --force  # Rebuild M2M

# Task system
uv run python manage.py fill_tasks              # Create tasks for duplicate covers
uv run python manage.py run_tasks               # Process tasks (crawl + update)
uv run python manage.py add_long_term <nid>     # Add novel as long-term task
uv run python manage.py remove_long_term <nid>  # Remove long-term task

# Snapshot system
uv run python manage.py smart_snapshot          # Create daily snapshots
uv run python manage.py archive_snapshots       # Archive last month to JSONL/CSV
uv run python manage.py archive_snapshots --month 2026-01  # Archive specific month

# Fix data
uv run python manage.py fix_ptype ../release/dataset/  # Fix ptype (upgrade only)

# Static site
uv run python manage.py generate_static --output ../build --base-path novel_hub
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
- **Database-specific**: PostgreSQL uses `execute_values` for bulk ops; SQLite uses PRAGMA tuning

### init_db

- Deletes ALL existing data before loading (clean initialization)
- Reads cover prefix from `site_config.toml` (not hardcoded)
- Strips URL prefix to save DB space
- Converts `nan` strings to `NULL`
- Timestamps in milliseconds (`unit='ms'`)
- Auto-loads `tasks.csv` when loading from directory

### upsert_dataset

- Updates existing records, inserts new ones
- Uses `ON CONFLICT UPDATE` (PostgreSQL) or `update_or_create` (SQLite)

## Data Rules

- **Died status**: `status == 连载中` + `last_update` >= 3 months ago → `died`
- **A status** (pseudo): `died` or `finished` + (`has_banner` OR `click >= 1000w` OR `review >= 60` OR `like >= 1w` OR `praise >= 1w`) → `断更A` / `完结A`
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
