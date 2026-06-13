"""Update database from a dataset file (INSERT + UPDATE).

Supports CSV and JSONL input. Auto-detects database type
and delegates to load_psql or load_sqlite.

Usage:
    uv run python manage.py load_dataset o.csv
    uv run python manage.py load_dataset data.jsonl --limit 1000
    uv run python manage.py load_dataset data.csv --force
"""

from pathlib import Path

from django.db import connection
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update database from a dataset file (CSV or JSONL)"

    def add_arguments(self, parser):
        parser.add_argument("path", help="Dataset file (CSV or JSONL)")
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit records (0 = all)"
        )
        parser.add_argument(
            "--force", action="store_true", help="Also reload tasks.csv"
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        is_psql = connection.vendor == "postgresql"
        cmd = "load_psql" if is_psql else "load_sqlite"
        self.stdout.write(f"Delegating to {cmd} ...")
        call_command(
            cmd,
            str(path),
            limit=options["limit"],
            force=options["force"],
        )
