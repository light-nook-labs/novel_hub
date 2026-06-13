"""PostgreSQL-only: Initialize database from release dataset.

Uses COPY for maximum throughput, drops/rebuilds indexes around load,
and runs ANALYZE after bulk insert for fresh planner statistics.

Usage:
    uv run python manage.py init_psql
    uv run python manage.py init_psql --limit 1000
    uv run python manage.py init_psql --path ../release/dataset
"""

import time
from pathlib import Path

from django.db import connection
from django.core.management.base import BaseCommand

from novels.management.utils import get_cover_prefix, NOVEL_COLUMNS
from novels.management.utils.logging import log_timing
from novels.management.utils.pandas_utils import (
    extract_entities,
    load_novels,
    build_novel_rows,
)
from novels.management.utils.psql_utils import (
    insert_simple,
    insert_novels,
    load_maps,
    drop_indexes,
    rebuild_indexes,
    analyze_tables,
    set_session_tuning,
    set_maintenance_tuning,
)


class Command(BaseCommand):
    help = "PostgreSQL-only: Initialize database from release dataset (COPY)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="../release/dataset",
            help="JSONL directory (default: ../release/dataset)",
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="Limit records (0 = all)"
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR(
                    "This command is PostgreSQL-only. Use init_sqlite for SQLite."
                )
            )
            return

        self.stdout.write("Starting PostgreSQL initialization")
        t0 = time.perf_counter()

        path = Path(options["path"])
        limit = options["limit"]

        files = sorted(path.glob("*.jsonl"))
        if not files:
            self.stderr.write(self.style.ERROR(f"No JSONL files found at {path}"))
            return

        cover_prefix = get_cover_prefix()
        self.stdout.write("Mode: INIT (COPY only)")
        self.stdout.write(f"Cover prefix: {cover_prefix}")
        self.stdout.write(f"Loading {len(files)} files from {path}")

        novel_count, tag_count = self._psql_init(files, cover_prefix, limit)

        elapsed = time.perf_counter() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed:.1f}s — {novel_count} novels, {tag_count} tag links"
            )
        )

    def _psql_init(self, files, cover_prefix, limit):
        """PostgreSQL 2-phase init with COPY + index management."""
        # Phase 1: Extract entities and insert simple tables
        self.stdout.write("  Phase 1: Extracting entities")
        t_phase = time.perf_counter()

        authors, contests, tags = self._extract_entities(files, limit)

        with connection.cursor() as cursor:
            set_session_tuning(cursor)
            self._insert_authors(cursor, authors)
            self._insert_contests(cursor, contests)
            self._insert_tags(cursor, tags)
            author_map, contest_map, tag_map = self._load_maps(cursor)

        phase1_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 1 completed ({phase1_time:.2f}s)")

        # Phase 2: Load novels with COPY, drop/rebuild indexes
        self.stdout.write("  Phase 2: Loading novels")
        t_phase = time.perf_counter()

        df, tag_rows = self._load_novels(
            files, cover_prefix, author_map, contest_map, tag_map, limit
        )
        novel_rows = self._build_novel_rows(df)

        with connection.cursor() as cursor:
            set_session_tuning(cursor)
            set_maintenance_tuning(cursor)

            saved = self._drop_indexes(cursor, "novels_novel")
            self._insert_novels(cursor, novel_rows)
            self._insert_m2m(cursor, tag_rows)
            self._rebuild_indexes(cursor, saved)

            # Fresh statistics for query planner
            self._analyze(cursor)

        phase2_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 2 completed ({phase2_time:.2f}s)")

        return len(df), len(tag_rows)

    @log_timing("Extract entities")
    def _extract_entities(self, files, limit):
        return extract_entities(files, limit)

    @log_timing("Insert authors")
    def _insert_authors(self, cursor, authors):
        insert_simple(cursor, "novels_author", ("name",), [(a,) for a in authors])

    @log_timing("Insert contests")
    def _insert_contests(self, cursor, contests):
        insert_simple(cursor, "novels_contest", ("name",), [(c,) for c in contests])

    @log_timing("Insert tags")
    def _insert_tags(self, cursor, tags):
        insert_simple(cursor, "novels_tag", ("name",), [(t,) for t in tags])

    @log_timing("Load maps")
    def _load_maps(self, cursor):
        return load_maps(cursor)

    @log_timing("Load novels")
    def _load_novels(
        self, files, cover_prefix, author_map, contest_map, tag_map, limit
    ):
        return load_novels(files, cover_prefix, author_map, contest_map, tag_map, limit)

    @log_timing("Build novel rows")
    def _build_novel_rows(self, df):
        return build_novel_rows(df)

    @log_timing("Drop indexes")
    def _drop_indexes(self, cursor, table):
        return drop_indexes(cursor, table)

    @log_timing("Insert novels (COPY)")
    def _insert_novels(self, cursor, novel_rows):
        insert_novels(cursor, NOVEL_COLUMNS, novel_rows)

    @log_timing("Insert M2M (COPY)")
    def _insert_m2m(self, cursor, tag_rows):
        insert_simple(cursor, "novels_novel_tags", ("novel_id", "tag_id"), tag_rows)

    @log_timing("Rebuild indexes")
    def _rebuild_indexes(self, cursor, saved):
        rebuild_indexes(cursor, saved)

    @log_timing("ANALYZE")
    def _analyze(self, cursor):
        analyze_tables(
            cursor,
            [
                "novels_novel",
                "novels_author",
                "novels_tag",
                "novels_contest",
                "novels_novel_tags",
            ],
        )
