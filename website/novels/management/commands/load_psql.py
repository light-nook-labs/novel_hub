"""PostgreSQL-only: Update database from JSONL files (INSERT + UPDATE).

Uses COPY for bulk inserts, execute_values for upserts, and ANALYZE
after bulk load for fresh planner statistics.

Usage:
    uv run python manage.py load_psql /tmp/spider_data.jsonl
    uv run python manage.py load_psql /tmp/spider_data.jsonl --limit 1000
    uv run python manage.py load_psql ../release/dataset/ --force
"""

import csv
import time
from pathlib import Path

from django.db import connection
from django.core.management.base import BaseCommand

from novels.models import Task
from novels.management.utils import (
    get_cover_prefix,
    NOVEL_COLUMNS,
    NOVEL_UPDATE_COLUMNS,
)
from novels.management.utils.logging import log_timing
from novels.management.utils.pandas_utils import (
    extract_entities,
    load_novels,
    build_novel_rows,
)
from novels.management.utils.psql_utils import (
    upsert_simple,
    upsert_novels,
    load_maps,
    analyze_tables,
    set_session_tuning,
)


class Command(BaseCommand):
    help = "PostgreSQL-only: Update database from JSONL files (COPY + UPSERT)"

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
        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR(
                    "This command is PostgreSQL-only. Use load_sqlite for SQLite."
                )
            )
            return

        self.stdout.write("Starting PostgreSQL update")
        t0 = time.perf_counter()

        path = Path(options["path"])
        limit = options["limit"]

        if path.is_dir():
            files = sorted(path.glob("*.jsonl"))
        else:
            files = [path]

        if not files:
            self.stderr.write(self.style.ERROR(f"No JSONL files found at {path}"))
            return

        cover_prefix = get_cover_prefix()
        self.stdout.write("Mode: UPDATE (COPY + UPSERT)")
        self.stdout.write(f"Cover prefix: {cover_prefix}")
        self.stdout.write(f"Loading {len(files)} files from {path}")

        novel_count, tag_count = self._psql_update(files, cover_prefix, limit)

        self._load_tasks(path, force=options["force"])

        elapsed = time.perf_counter() - t0
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed:.1f}s — {novel_count} novels, {tag_count} tag links"
            )
        )

    def _psql_update(self, files, cover_prefix, limit):
        """PostgreSQL 2-phase update with session tuning + ANALYZE."""
        # Phase 1: Extract entities
        self.stdout.write("  Phase 1: Extracting entities")
        t_phase = time.perf_counter()

        authors, contests, tags = self._extract_entities(files, limit)

        with connection.cursor() as cursor:
            set_session_tuning(cursor)
            self._upsert_authors(cursor, authors)
            self._upsert_contests(cursor, contests)
            self._upsert_tags(cursor, tags)
            author_map, contest_map, tag_map = self._load_maps(cursor)

        phase1_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 1 completed ({phase1_time:.2f}s)")

        # Phase 2: Load novels
        self.stdout.write("  Phase 2: Loading novels")
        t_phase = time.perf_counter()

        df, tag_rows = self._load_novels(
            files, cover_prefix, author_map, contest_map, tag_map, limit
        )
        novel_rows = self._build_novel_rows(df)

        with connection.cursor() as cursor:
            set_session_tuning(cursor)
            self._upsert_novels(cursor, novel_rows)
            self._upsert_m2m(cursor, tag_rows)
            self._analyze(cursor)

        phase2_time = time.perf_counter() - t_phase
        self.stdout.write(f"  Phase 2 completed ({phase2_time:.2f}s)")

        return len(df), len(tag_rows)

    @log_timing("Extract entities")
    def _extract_entities(self, files, limit):
        return extract_entities(files, limit)

    @log_timing("Upsert authors")
    def _upsert_authors(self, cursor, authors):
        upsert_simple(cursor, "novels_author", ("name",), [(a,) for a in authors])

    @log_timing("Upsert contests")
    def _upsert_contests(self, cursor, contests):
        upsert_simple(cursor, "novels_contest", ("name",), [(c,) for c in contests])

    @log_timing("Upsert tags")
    def _upsert_tags(self, cursor, tags):
        upsert_simple(cursor, "novels_tag", ("name",), [(t,) for t in tags])

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

    @log_timing("Upsert novels")
    def _upsert_novels(self, cursor, novel_rows):
        upsert_novels(cursor, NOVEL_COLUMNS, novel_rows, NOVEL_UPDATE_COLUMNS)

    @log_timing("Upsert M2M")
    def _upsert_m2m(self, cursor, tag_rows):
        upsert_simple(cursor, "novels_novel_tags", ("novel_id", "tag_id"), tag_rows)

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

    def _load_tasks(self, path, force=False):
        """Load tasks.csv if exists."""
        if not path.is_dir():
            return
        if not force:
            self.stdout.write("  Tasks: skipped (use --force)")
            return

        tasks_file = path / "tasks.csv"
        if not tasks_file.exists():
            tasks_file = path.parent / "tasks.csv"
        if not tasks_file.exists():
            self.stdout.write("  tasks.csv not found")
            return

        t_step = time.perf_counter()
        batch = []
        total = 0
        Task.objects.all().delete()

        with open(tasks_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                batch.append(Task(novel_id=int(row["novel_id"]), status=row["status"]))
                if len(batch) >= 5000:
                    Task.objects.bulk_create(batch, ignore_conflicts=True)
                    total += len(batch)
                    batch = []
        if batch:
            Task.objects.bulk_create(batch, ignore_conflicts=True)
            total += len(batch)

        elapsed = time.perf_counter() - t_step
        self.stdout.write(f"  Tasks loaded: {total} records ({elapsed:.2f}s)")
