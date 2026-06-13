"""Update database from JSONL files (INSERT + UPDATE).

Auto-detects database type and delegates to load_psql or load_sqlite.

Usage:
    uv run python manage.py load_jsonl /tmp/spider_data.jsonl
    uv run python manage.py load_jsonl /tmp/spider_data.jsonl --limit 1000
    uv run python manage.py load_jsonl ../release/dataset/ --force
"""

from django.db import connection
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update database from JSONL files (auto-detect DB type)"

    def add_arguments(self, parser):
        parser.add_argument(
            "path", nargs="?", default="dataset/data", help="JSONL file or directory"
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit records (0 = all)"
        )
        parser.add_argument(
            "--force", action="store_true", help="Also reload tasks.csv"
        )

    def handle(self, *args, **options):
        is_psql = connection.vendor == "postgresql"
        cmd = "load_psql" if is_psql else "load_sqlite"
        self.stdout.write(f"Delegating to {cmd} ...")
        call_command(
            cmd,
            path=options["path"],
            limit=options["limit"],
            force=options["force"],
        )
