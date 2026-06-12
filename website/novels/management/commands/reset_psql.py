"""Reset PostgreSQL database and load limited data for testing.

WARNING: This command will TRUNCATE all tables in PostgreSQL.
DO NOT run without explicit approval.
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = "Clear all tables in PostgreSQL and reload limited data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Number of records to load (default: 100)",
        )
        parser.add_argument(
            "--path",
            type=str,
            default="../release/dataset",
            help="JSONL directory (default: ../release/dataset)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        path = options["path"]

        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR("This command only works with PostgreSQL")
            )
            return

        self.stdout.write("Clearing PostgreSQL tables ...")
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE novels_novel_tags CASCADE")
            cursor.execute("TRUNCATE novels_novel CASCADE")
            cursor.execute("TRUNCATE novels_author CASCADE")
            cursor.execute("TRUNCATE novels_tag CASCADE")
            cursor.execute("TRUNCATE novels_contest CASCADE")
            cursor.execute("TRUNCATE novels_task CASCADE")
        self.stdout.write(self.style.SUCCESS("  Tables truncated"))

        self.stdout.write(f"Loading {limit} records from {path} ...")
        call_command("load_jsonl", path, limit=limit)

        self.stdout.write(self.style.SUCCESS(f"Done — loaded {limit} records"))
