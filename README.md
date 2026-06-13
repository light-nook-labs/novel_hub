# Novel Hub

A novel metadata website for sfacg.com, built with Django + Tailwind CSS.

## Features

- Novel browsing and search
- Filter by genre, status, and ptype
- Multi-dimensional rankings (clicks, words, favorites, etc.)
- Author, tag, and contest browsing
- Banner novel showcase
- Dark mode support
- Mobile-responsive design
- Static site generation for GitHub Pages

## Tech Stack

- **Backend**: Django 6.0 + Python 3.13
- **Frontend**: Tailwind CSS 4.x
- **Database**: SQLite (dev) / PostgreSQL (Supabase prod)
- **Data Collection**: Scrapy + pandas
- **Deployment**: Docker / GitHub Actions + GitHub Pages

## Database ER Diagram

```mermaid
erDiagram
    Author {
        CharField name UK "unique"
    }

    Tag {
        CharField name UK "unique"
    }

    Contest {
        CharField name UK "unique"
    }

    Novel {
        BigIntegerField id PK "sfacg nid"
        CharField title
        SmallIntegerField ptype INDEX
        SmallIntegerField genre INDEX
        SmallIntegerField status INDEX
        IntegerField click_num
        IntegerField word_num
        IntegerField praise_num
        IntegerField like_num
        BooleanField has_banner INDEX
        IntegerField review_num
        IntegerField comment_num
        CharField cover
        DateTimeField last_update
        DateTimeField db_update "auto_now"
    }

    Task {
        CharField status "u=urgent d=default f=finished"
    }

    Author ||--o{ Novel : "1:N"
    Contest ||--o{ Novel : "1:N"
    Novel }o--o{ Tag : "M2M"
    Novel ||--o| Task : "1:0..1"
```

### Relationships
1. Author  : Novel  →  One-to-Many (`ForeignKey`, `on_delete=SET_NULL`)
2. Contest : Novel  →  One-to-Many (`ForeignKey`, `on_delete=SET_NULL`)
3. Novel   : Tag    →  Many-to-Many (`ManyToManyField`)
4. Novel   : Task   →  One-to-One (`OneToOneField`, `on_delete=CASCADE`)

### Mappings (Context Processor)

Enum fields `ptype`, `genre`, `status` store integer values mapped via `Mapping` class:

| Field   | Values (en → zh)                              |
|---------|-----------------------------------------------|
| genre   | magic→魔幻, eastern→玄幻, ancient→古风, sci_fi→科幻, school→校园, urban→都市, game→游戏, doujin→同人, mystery→悬疑 |
| status  | finished→已完结, on_going→连载中, died→断更, active_d→断更A, active_f→完结A, removed→下架 |
| ptype   | free→免费, sign→签约, vip→VIP                 |

Unknown values fall back to `OTHER` (index 1).

## Quick Start

### Local Development

```bash
# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Load sample data
uv run python manage.py create_fake_data -n 1000

# Start development server
uv run python manage.py runserver

# Build Tailwind CSS
pnpm build
```

### Docker

```bash
# Build and run
docker compose up -d --build

# Access at http://localhost:8000

# View logs
docker compose logs -f web

# Stop
docker compose down
```

## Data Loading

For development with fake data:
```bash
uv run python manage.py create_fake_data -n 1000
```

For real data (from release):
```bash
gh release download v1.1.0 --repo light-nook-labs/novel_hub --pattern '*.tar.gz'
tar -xzf release-v1.1.0.tar.gz
uv run python manage.py init_db release/dataset/    # Init (deletes all data first)
uv run python manage.py upsert_dataset release/dataset/  # Upsert (updates existing)
uv run python manage.py dump_dataset release                 # Dump DB
```

## Data Dump

Dump database to release format:
```bash
uv run python manage.py dump_jsonl release
```

Output structure:
```
release/
├── dataset/
│   ├── meta_01.jsonl   # 20k records each
│   ├── ...
│   └── meta_13.jsonl
└── tasks.csv
```

## Static Site Generation

Generate static HTML for GitHub Pages:
```bash
uv run python manage.py generate_static --output ../build --base-path novel_hub
```

Preview locally:
```bash
uv run python manage.py serve_static --port 8080
```

## Testing

```bash
uv run python manage.py test novels -v 2
```

51 unit tests covering views, models, and mappings.

## License

MIT
