"""Initialize database from release dataset.

Auto-detects database type and delegates to init_psql or init_sqlite.

Usage:
    uv run python manage.py init_db
    uv run python manage.py init_db --limit 1000
"""

from django.db import connection
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Initialize database from release dataset (auto-detect DB type)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="../release/jsonl",
            help="JSONL directory (default: ../release/jsonl)",
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit records (0 = all)"
        )

    def handle(self, *args, **options):
        is_psql = connection.vendor == "postgresql"
        cmd = "init_psql" if is_psql else "init_sqlite"
        self.stdout.write(f"Delegating to {cmd} ...")
        call_command(cmd, path=options["path"], limit=options["limit"])
