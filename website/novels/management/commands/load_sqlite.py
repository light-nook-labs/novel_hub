"""SQLite-only: Update database from a JSONL file (INSERT + UPDATE).

Uses ORM with WAL mode and optimized PRAGMAs.

Usage:
    uv run python manage.py load_sqlite /tmp/spider_data.jsonl
    uv run python manage.py load_sqlite /tmp/spider_data.jsonl --limit 1000
    uv run python manage.py load_sqlite /tmp/spider_data.jsonl --force
"""

import time
from pathlib import Path

from django.db import connection
from django.core.management.base import BaseCommand

from novels.management.utils import get_cover_prefix
from novels.management.utils.logging import log_timing
from novels.management.utils.pandas_utils import (
    extract_entities,
    load_novels,
)
from novels.management.utils.sqlite_utils import (
    enable_wal_mode,
    optimize,
    bulk_create_authors,
    bulk_create_contests,
    bulk_create_tags,
    bulk_create_novels,
    bulk_insert_tags,
)
from novels.management.utils.tasks_utils import load_tasks_from_csv


class Command(BaseCommand):
    help = "SQLite-only: Update database from a JSONL file (ORM)"

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSONL file path")
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit records (0 = all)"
        )
        parser.add_argument(
            "--force", action="store_true", help="Also reload tasks.csv"
        )

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            self.stderr.write(
                self.style.ERROR(
                    "This command is SQLite-only. Use load_psql for PostgreSQL."
                )
            )
            return

        path = Path(options["path"])
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        self.stdout.write("Starting SQLite update")
        t0 = time.perf_counter()

        limit = options["limit"]
        files = [path]

        cover_prefix = get_cover_prefix()
        self.stdout.write("Mode: UPDATE (ORM bulk_create)")
        self.stdout.write(f"Cover prefix: {cover_prefix}")
        self.stdout.write(f"Loading {path}")

        enable_wal_mode()
        novel_count, tag_count = self._sqlite_update(files, cover_prefix, limit)
        optimize()

        load_tasks_from_csv(path.parent, self.stdout, force=options["force"])

        elapsed = time.perf_counter() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed:.1f}s — {novel_count} novels, {tag_count} tag links"
            )
        )

    def _sqlite_update(self, files, cover_prefix, limit):
        """SQLite 2-phase update with ORM."""
        self.stdout.write("  Phase 1: Extracting entities")
        t_phase = time.perf_counter()

        authors, contests, tags = self._extract_entities(files, limit)
        author_map = self._bulk_create_authors(authors)
        contest_map = self._bulk_create_contests(contests)
        tag_map = self._bulk_create_tags(tags)

        phase1_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 1 completed ({phase1_time:.2f}s)")

        self.stdout.write("  Phase 2: Loading novels")
        t_phase = time.perf_counter()

        df, tag_rows = self._load_novels(
            files, cover_prefix, author_map, contest_map, tag_map, limit
        )
        self._bulk_create_novels(df, author_map, contest_map)
        self._bulk_insert_tags(tag_rows)

        phase2_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 2 completed ({phase2_time:.2f}s)")

        return len(df), len(tag_rows)

    @log_timing("Extract entities")
    def _extract_entities(self, files, limit):
        return extract_entities(files, limit)

    @log_timing("Bulk create authors")
    def _bulk_create_authors(self, authors):
        return bulk_create_authors(authors, 10000)

    @log_timing("Bulk create contests")
    def _bulk_create_contests(self, contests):
        return bulk_create_contests(contests, 10000)

    @log_timing("Bulk create tags")
    def _bulk_create_tags(self, tags):
        return bulk_create_tags(tags, 10000)

    @log_timing("Load novels")
    def _load_novels(
        self, files, cover_prefix, author_map, contest_map, tag_map, limit
    ):
        return load_novels(files, cover_prefix, author_map, contest_map, tag_map, limit)

    @log_timing("Bulk create novels")
    def _bulk_create_novels(self, df, author_map, contest_map):
        bulk_create_novels(df, author_map, contest_map, 10000)

    @log_timing("Bulk insert tags")
    def _bulk_insert_tags(self, tag_rows):
        bulk_insert_tags(tag_rows)
