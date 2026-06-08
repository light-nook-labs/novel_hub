---
name: docker-deploy
description: Docker build, run, and deployment operations for the learning_log project
---

## What I do
- Build Docker image
- Run containers with docker-compose
- Manage volumes and environment variables
- View logs and debug containers

## Commands

### Build
```bash
docker-compose build
```

### Run
```bash
docker-compose up -d
```

### Stop
```bash
docker-compose down
```

### Logs
```bash
docker-compose logs -f web
```

### Shell access
```bash
docker-compose exec web python manage.py shell
```

### Migrations
```bash
docker-compose exec web python manage.py migrate
```

### Collect static
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## Environment
- `.env` file contains configuration
- `SECRET_KEY` is required (no default)
- See `.env.example` for all options

## Volumes
- `./db.sqlite3` — SQLite database
- `./static` — static files
- `./media` — user uploads
