# website

Django project for Novel Hub. Web application, data processing commands, and static site generation.

## Tech Stack

### Backend

- **Django** — web framework, ORM, admin, template engine
- **pandas** — JSONL/CSV data loading and processing
- **plotly** — Dashboard charts
- **requests** — HTTP client for task runner
- **python-dotenv** — Environment variables
- **psycopg2-binary** — PostgreSQL driver
- **utils/** — loader, Meta model, fetch_html, fetch_api, mappings, logger

### Frontend

- **Tailwind CSS** — CSS framework
- **htmx.org** — Dynamic interactions without JavaScript

## Quick Start

```bash
uv run python manage.py migrate
uv run python manage.py init_db ../release/dataset/
uv run python manage.py runserver
```

## Structure

```
website/
├── manage.py
├── config/                     # Django settings, urls, wsgi
│   ├── settings.py             # Loads .env + site_config.toml
│   └── toml.py                 # TOML reader
├── templates/                  # Project-level base template
│   └── base.html               # HTML skeleton, global assets
└── novels/                     # Main Django app
    ├── models.py               # Novel, Author, Tag, Contest, Task, NovelSnapshot
    ├── views/                  # ListView, DetailView for all pages
    ├── mappings.py             # Re-exports GENRE/STATUS/PTYPE from utils
    ├── admin.py                # Django admin
    ├── templatetags/           # cover_url, humanize_num, pill_bg, etc.
    ├── management/
    │   └── commands/           # init_db, upsert_dataset, run_tasks, etc.
    ├── templates/              # App-level templates
    └── tests/                  # Unit and E2E tests
```

## Sub-modules

| Module | README | Description |
|--------|--------|-------------|
| `novels/views/` | [views/README.md](novels/views/README.md) | Routes and query parameters |
| `novels/templates/` | [templates/README.md](novels/templates/novels/README.md) | Template inheritance and components |
| `novels/management/commands/` | [commands/README.md](novels/management/commands/README.md) | Management commands |
| `novels/tests/` | [tests/README.md](novels/tests/README.md) | Test coverage |

## Docs

See [docs/website.md](../docs/website.md) for detailed documentation.
