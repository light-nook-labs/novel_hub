# Deployment

Deployment guide for Novel Hub.

> **Quick overview**: See [README.md](../README.md)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
SECRET_KEY=your-secret-key
DEBUG=0

# SQLite (development)
DB_TYPE=sqlite

# PostgreSQL (production)
# DB_TYPE=postgresql
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=novel_hub
# DB_USER=postgres
# DB_PASSWORD=your-password
```

## Docker

### Build and Run

```bash
# Build image
docker compose build

# Start container
docker compose up -d

# Access at http://localhost:8000

# View logs
docker compose logs -f web

# Stop
docker compose down
```

### docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - db-data:/app/website
    restart: unless-stopped

volumes:
  db-data:
```

### Dockerfile

```dockerfile
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Node.js + pnpm
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g pnpm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Build Tailwind CSS
RUN cd website && pnpm install --frozen && pnpm build

# Collect static files
RUN cd website && uv run python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

CMD ["uv", "run", "--directory", "website", "python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Init Database in Docker

```bash
# Copy dataset to container
docker compose cp ../release/dataset web:/app/release/dataset

# Init database
docker compose exec web uv run python website/manage.py init_db /app/release/dataset/

# Or from release archive
docker compose exec web uv run python website/manage.py init_from_release /app/release.tar.gz
```

## GitHub Actions

### Workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `test.yml` | Push/PR to main | Run tests |
| `crawl-upsert.yml` | Daily 02:00 Shanghai | Crawl novels and upsert to DB |
| `run-tasks.yml` | Daily 01:00 Shanghai | Process task queue |
| `daily-snapshot.yml` | Daily 04:00 Shanghai | Create daily snapshots |
| `process-task-issues.yml` | Daily 03:00 Shanghai | Process GitHub issues |
| `deploy-ssg.yml` | After test + crawl | Deploy static site to GitHub Pages |
| `monthly-archive.yml` | 1st of month 05:00 Shanghai | Archive snapshots |
| `publish-release.yml` | 1st of month 04:00 Shanghai | Publish release archive |

### Required Secrets

| Secret | Description |
|--------|-------------|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `SECRET_KEY` | Django secret key |

### Deploy Static Site

```bash
# Manual trigger
gh workflow run deploy-ssg.yml

# Or push to main (runs after tests pass)
git push origin main
```

## GitHub Pages

Static site is deployed to GitHub Pages via `deploy-ssg.yml`:

1. Tests pass
2. Crawl & upsert completes
3. Generate static pages
4. Deploy to `gh-pages` branch

Access at: `https://light-nook-labs.github.io/novel_hub/`

## Production Checklist

- [ ] Set `DEBUG=0` in `.env`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up HTTPS (reverse proxy)
- [ ] Configure backups
