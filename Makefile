.PHONY: setup spider runserver makemigrations migrate createsuperuser test lint dev build \
       init_db init_from_release upsert_dataset dump_dataset create_release \
       fix_m2m fix_ptype \
       fill_tasks run_tasks add_long_term remove_long_term process_task_issues \
       smart_snapshot archive_snapshots \
       generate_static preview

setup:
	uv sync
	pnpm install

# Spider
spider:
	cd meta_spider && uv run scrapy crawl meta_batch -o o.jsonl \
		-a num=$(or $(NUM),10) \
		-a begin=$(or $(BEGIN),1) \
		-a days=$(or $(DAYS),7)

# Development
runserver:
	uv run python website/manage.py runserver $(PORT)

makemigrations:
	uv run python website/manage.py makemigrations

migrate:
	uv run python website/manage.py migrate

createsuperuser:
	uv run python website/manage.py createsuperuser

test:
	uv run python website/manage.py test novels -v 2

lint:
	uv run black .
	uv run flake8 .

# Tailwind CSS
dev:
	pnpm dev

build:
	pnpm build

# Data
init_db:
	uv run python website/manage.py init_db $(or $(PATH),../release/dataset/)

init_from_release:
	uv run python website/manage.py init_from_release $(URL)

upsert_dataset:
	uv run python website/manage.py upsert_dataset $(or $(PATH),../release/dataset/)

dump_dataset:
	uv run python website/manage.py dump_dataset $(or $(PATH),release)

create_release:
	uv run python website/manage.py create_release --output $(or $(OUT),../release.tar.gz)

fix_m2m:
	uv run python website/manage.py fix_m2m $(or $(PATH),../release/dataset/) --force

fix_ptype:
	uv run python website/manage.py fix_ptype $(or $(PATH),../release/dataset/)

# Tasks
fill_tasks:
	uv run python website/manage.py fill_tasks

run_tasks:
	uv run python website/manage.py run_tasks --limit $(or $(LIMIT),500)

add_long_term:
	uv run python website/manage.py add_long_term $(NID)

remove_long_term:
	uv run python website/manage.py remove_long_term $(NID)

process_task_issues:
	uv run python website/manage.py process_task_issues

# Snapshots
smart_snapshot:
	uv run python website/manage.py smart_snapshot

archive_snapshots:
	uv run python website/manage.py archive_snapshots $(if $(MONTH),--month $(MONTH))

# Static site
generate_static:
	uv run python website/manage.py generate_static --output $(or $(OUT),../build) --base-path $(or $(BASE),novel_hub) --workers $(or $(WORKERS),4)

preview:
	uv run python website/manage.py serve_static --port $(or $(PORT),8080)
