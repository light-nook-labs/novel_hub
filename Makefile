.PHONY: dev static serve test lint clean docker-build docker-up docker-down

# Development
dev:
	cd website && uv run python manage.py runserver

# Static site generation (local preview)
static:
	cd website && uv run python manage.py generate_static --output ../build

# Serve static site (foreground, Ctrl+C to stop)
serve:
	cd website && uv run python manage.py serve_static --dir ../build


# Run tests
test:
	cd website && uv run python manage.py test novels -v 2

# Lint
lint:
	cd website && uv run black . && uv run flake8 .

# Clean
clean:
	rm -rf build
	rm -f website/db.sqlite3

# Load data to PostgreSQL
load-data:
	cd website && uv run python manage.py load_dataset ../release/dataset/meta_13.jsonl

# Load data to SQLite
load-data-sqlite:
	@echo "DB_TYPE=sqlite" > /tmp/.env_tmp
	@echo "SECRET_KEY=dev-secret-key" >> /tmp/.env_tmp
	@echo "DEBUG=1" >> /tmp/.env_tmp
	cd website && DB_TYPE=sqlite uv run python manage.py load_dataset ../release/dataset/meta_13.jsonl

# Tailwind CSS
tailwind:
	cd website && pnpm dev

tailwind-build:
	cd website && pnpm build

# Docker
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
