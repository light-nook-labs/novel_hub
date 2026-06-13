"""Reset PostgreSQL database.

WARNING: This command will TRUNCATE all tables in PostgreSQL.
DO NOT run without explicit approval.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Clear all tables in PostgreSQL"

    def handle(self, *args, **options):
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
