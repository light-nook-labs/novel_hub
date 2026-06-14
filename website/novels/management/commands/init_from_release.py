"""Management command to initialize database from release tar archive.

Deletes ALL existing data before loading. Use for clean initialization.

The archive should contain:
- jsonl/meta_*.jsonl — JSONL dataset files
- csv/meta_*.csv — CSV dataset files (optional)
- tasks.csv — Task data (optional)

Usage:
    uv run python manage.py init_from_release <archive>

Examples:
    uv run python manage.py init_from_release ../release.tar.gz
    uv run python manage.py init_from_release https://github.com/light-nook-labs/novel_hub/releases/latest/download/release.tar.gz
"""

import csv
import io
import tarfile
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from novels.models import Author, Contest, Novel, Tag, Task

from utils import loader
from utils.logger import get_logger, progress
from utils.models import Meta

logger = get_logger(__name__)


class Command(BaseCommand):
    help = (
        "Initialize database from release tar archive (deletes all existing data first)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "archive",
            type=str,
            help="Path to release.tar.gz or URL",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for bulk operations (default: 1000)",
        )
        parser.add_argument(
            "--skip-tasks",
            action="store_true",
            help="Skip loading tasks.csv",
        )

    def handle(self, *args, **options):
        archive_path = options["archive"]
        batch_size = options["batch_size"]
        skip_tasks = options["skip_tasks"]

        # Detect database type
        db_type = settings.DATABASES["default"]["ENGINE"]
        is_postgres = "postgresql" in db_type

        if is_postgres:
            from utils.loader_postgres import bulk_create_ignore, bulk_create_m2m
        else:
            from utils.loader_sqlite import bulk_create_ignore, bulk_create_m2m

        # Step 1: Open archive
        logger.info("Opening archive: %s", archive_path)
        tar = self._open_archive(archive_path)

        # Step 2: Load JSONL data BEFORE deleting anything
        logger.info("Loading JSONL data from archive...")
        jsonl_files = sorted([f for f in tar.getnames() if f.endswith(".jsonl")])

        if not jsonl_files:
            raise CommandError("No JSONL files found in archive")

        logger.info("Found %d JSONL files", len(jsonl_files))

        # Read all JSONL files into DataFrames
        import pandas as pd

        dfs = []
        for jsonl_file in progress(jsonl_files, desc="Reading JSONL"):
            f = tar.extractfile(jsonl_file)
            if f is None:
                continue
            content = f.read().decode("utf-8")
            df = pd.read_json(io.StringIO(content), lines=True)
            dfs.append(df)

        if not dfs:
            raise CommandError("Failed to read JSONL files")

        df = pd.concat(dfs, ignore_index=True)
        logger.info("Loaded %d records total", len(df))

        if df.empty:
            raise CommandError("No records found in dataset")

        # Step 3: Validate through Meta model
        logger.info("Validating data through Meta model...")
        meta_list = loader.df_to_meta_list(df)
        logger.info("Validated %d records", len(meta_list))

        if not meta_list:
            raise CommandError("No valid records after validation")

        # Step 4: Delete ALL existing data
        logger.info("Deleting all existing data...")
        with transaction.atomic():
            with connection.cursor() as cursor:
                if is_postgres:
                    cursor.execute(
                        "TRUNCATE TABLE novels_novel_tags, novels_task, novels_novel, novels_author, novels_tag, novels_contest CASCADE"
                    )
                else:
                    # SQLite: disable FK checks, delete all, re-enable
                    cursor.execute("PRAGMA foreign_keys = OFF")
                    cursor.execute("DELETE FROM novels_novel_tags")
                    cursor.execute("DELETE FROM novels_task")
                    cursor.execute("DELETE FROM novels_novel")
                    cursor.execute("DELETE FROM novels_author")
                    cursor.execute("DELETE FROM novels_tag")
                    cursor.execute("DELETE FROM novels_contest")
                    cursor.execute("PRAGMA foreign_keys = ON")
        logger.info("All data deleted")

        # Step 5: Extract unique entities
        logger.info("Extracting unique entities...")
        authors = loader.extract_authors(df)
        tags = loader.extract_tags(df)
        contests = loader.extract_contests(df)
        logger.info(
            "Found %d authors, %d tags, %d contests",
            len(authors),
            len(tags),
            len(contests),
        )

        # Step 6: Create entities
        with transaction.atomic():
            # Create Authors
            logger.info("Creating authors...")
            author_objs = [Author(name=name) for name in authors]
            bulk_create_ignore(Author, author_objs, batch_size)
            logger.info("Created %d authors", len(author_objs))

            # Create Tags
            logger.info("Creating tags...")
            tag_objs = [Tag(name=name) for name in tags]
            bulk_create_ignore(Tag, tag_objs, batch_size)
            logger.info("Created %d tags", len(tag_objs))

            # Create Contests
            logger.info("Creating contests...")
            contest_objs = [Contest(name=name) for name in contests]
            bulk_create_ignore(Contest, contest_objs, batch_size)
            logger.info("Created %d contests", len(contest_objs))

        # Build lookup maps
        author_map = {a.name: a.id for a in Author.objects.all()}
        tag_map = {t.name: t.id for t in Tag.objects.all()}
        contest_map = {c.name: c.id for c in Contest.objects.all()}

        # Step 7: Create Novels
        logger.info("Creating novels...")
        novel_count = 0
        novel_tag_pairs = []
        batch = []
        # Use smaller batch size for SQLite to avoid SQL variable limits
        novel_batch_size = 100 if not is_postgres else batch_size

        for meta in progress(meta_list, desc="Creating novels"):
            django_data = meta.to_django_dict()

            # Resolve foreign keys
            author_name = django_data.pop("author", "")
            contest_name = django_data.pop("contest", None)
            tag_names = django_data.pop("tags", [])

            author_id = author_map.get(author_name)
            contest_id = contest_map.get(contest_name) if contest_name else None

            novel = Novel(
                id=django_data["id"],
                title=django_data["title"],
                author_id=author_id,
                contest_id=contest_id,
                genre=django_data.get("genre", 1),
                status=django_data.get("status", 1),
                ptype=django_data.get("ptype", 1),
                has_banner=django_data.get("has_banner", False),
                word_num=django_data.get("word_num"),
                click_num=django_data.get("click_num"),
                praise_num=django_data.get("praise_num"),
                like_num=django_data.get("like_num"),
                review_num=django_data.get("review_num"),
                comment_num=django_data.get("comment_num"),
                last_update=django_data.get("last_update"),
                cover=django_data.get("cover"),
            )
            batch.append(novel)

            # Collect M2M pairs
            for tag_name in tag_names:
                tag_id = tag_map.get(tag_name)
                if tag_id:
                    novel_tag_pairs.append((django_data["id"], tag_id))

            if len(batch) >= novel_batch_size:
                Novel.objects.bulk_create(batch, ignore_conflicts=True)
                novel_count += len(batch)
                batch = []

        # Create remaining
        if batch:
            Novel.objects.bulk_create(batch, ignore_conflicts=True)
            novel_count += len(batch)

        logger.info("Created %d novels", novel_count)

        # Step 8: Create M2M relationships
        logger.info(
            "Creating novel-tag relationships (%d pairs)...", len(novel_tag_pairs)
        )
        # Use smaller batch size for SQLite to avoid SQL variable limits
        m2m_batch_size = 100 if not is_postgres else batch_size
        m2m_objects = [
            Novel.tags.through(novel_id=nid, tag_id=tid) for nid, tid in novel_tag_pairs
        ]
        for i in range(0, len(m2m_objects), m2m_batch_size):
            batch = m2m_objects[i : i + m2m_batch_size]
            Novel.tags.through.objects.bulk_create(batch, ignore_conflicts=True)
        logger.info("Created %d novel-tag relationships", len(novel_tag_pairs))

        # Step 9: Load tasks if present and not skipped
        if not skip_tasks:
            tasks_file = "tasks.csv"
            try:
                f = tar.extractfile(tasks_file)
                if f:
                    content = f.read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content))
                    tasks = []
                    for row in reader:
                        novel_id = int(row["novel_id"])
                        if Novel.objects.filter(id=novel_id).exists():
                            tasks.append(
                                Task(novel_id=novel_id, status=Task.Status.DEFAULT)
                            )

                    if tasks:
                        with transaction.atomic():
                            Task.objects.bulk_create(tasks, ignore_conflicts=True)
                        logger.info("Created %d tasks", len(tasks))
            except KeyError:
                logger.info("No tasks.csv found in archive, skipping")

        tar.close()

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! "
                f"Authors: {Author.objects.count()}, "
                f"Tags: {Tag.objects.count()}, "
                f"Contests: {Contest.objects.count()}, "
                f"Novels: {Novel.objects.count()}, "
                f"Tasks: {Task.objects.count()}"
            )
        )

    def _open_archive(self, path):
        """Open tar archive from file path or URL."""
        if path.startswith("http://") or path.startswith("https://"):
            logger.info("Downloading archive from %s", path)
            resp = requests.get(path, timeout=300, stream=True)
            resp.raise_for_status()

            # Save to temp file
            import tempfile

            tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp.close()

            return tarfile.open(tmp.name, "r:gz")

        path = Path(path)
        if not path.exists():
            raise CommandError(f"Archive not found: {path}")

        return tarfile.open(path, "r:gz")
