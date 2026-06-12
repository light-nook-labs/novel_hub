.PHONY: dev static serve test lint clean reset-db docker-build docker-up docker-down

# Development
dev:
	cd website && uv run python manage.py runserver

# Static site generation
static:
	cd website && uv run python manage.py generate_static --output ../build --base-path novel_hub

# Serve static site (background)
serve:
	cd build && python3 -m http.server 3000 &
	@sleep 1
	@echo "Server started at http://127.0.0.1:3000"

# Stop static server
serve-stop:
	@pkill -f "http.server 3000" 2>/dev/null || true

# Test static site
test-serve: serve
	@echo "=== Testing static site ==="
	@curl -s http://127.0.0.1:3000/ | head -5
	@echo ""
	@echo "=== Checking rank page ==="
	@curl -s http://127.0.0.1:3000/rank/ | grep -oP '1970-01-01' | wc -l | xargs -I{} echo "Zero dates: {}"
	@echo ""
	@echo "=== Checking covers ==="
	@curl -s http://127.0.0.1:3000/ | grep -oP 'src="[^"]*"' | head -3
	@$(MAKE) serve-stop

# Test Django server
test-dev:
	@cd website && uv run python manage.py runserver 8081 &
	@sleep 2
	@echo "=== Testing Django server ==="
	@curl -s http://127.0.0.1:8081/ | head -5
	@echo ""
	@echo "=== Checking rank page ==="
	@curl -s "http://127.0.0.1:8081/rank/" | grep -oP '1970-01-01' | wc -l | xargs -I{} echo "Zero dates: {}"
	@pkill -f "runserver 8081" 2>/dev/null || true

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

# Reset PostgreSQL database
reset-db:
	cd website && uv run python manage.py reset_psql --limit 100

# Load data to PostgreSQL
load-data:
	cd website && uv run python manage.py load_jsonl ../release/dataset/meta_13.jsonl

# Load data to SQLite
load-data-sqlite:
	@echo "DB_TYPE=sqlite" > /tmp/.env_tmp
	@echo "SECRET_KEY=dev-secret-key" >> /tmp/.env_tmp
	@echo "DEBUG=1" >> /tmp/.env_tmp
	cd website && DB_TYPE=sqlite uv run python manage.py load_jsonl ../release/dataset/meta_13.jsonl

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
