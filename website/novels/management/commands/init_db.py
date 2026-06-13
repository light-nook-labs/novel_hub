"""Management command to initialize database from JSONL/CSV dataset.

Deletes ALL existing data before loading. Use for clean initialization.

Usage:
    uv run python manage.py init_db <path>

Examples:
    uv run python manage.py init_db ../release/dataset/
    uv run python manage.py init_db ../release/dataset/meta_01.jsonl
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from novels.models import Author, Contest, Novel, Tag

from utils import loader
from utils.logger import get_logger, progress
from utils.models import Meta

logger = get_logger(__name__)


class Command(BaseCommand):
    help = "Initialize database from JSONL/CSV dataset (deletes all existing data first)"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help="Path to JSONL file, directory containing meta_*.jsonl files, or CSV file",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for bulk operations (default: 1000)",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        batch_size = options["batch_size"]

        if not path.exists():
            raise CommandError(f"Path does not exist: {path}")

        # Detect database type
        db_type = settings.DATABASES["default"]["ENGINE"]
        is_postgres = "postgresql" in db_type

        if is_postgres:
            from utils.loader_postgres import bulk_create_ignore, bulk_create_m2m
        else:
            from utils.loader_sqlite import bulk_create_ignore, bulk_create_m2m

        # Step 1: Load and validate data BEFORE deleting anything
        logger.info("Loading data from %s", path)
        if path.suffix == ".csv":
            df = loader.load_csv(path)
        else:
            df = loader.load_jsonl(path)
        logger.info("Loaded %d records", len(df))

        if df.empty:
            raise CommandError("No records found in dataset")

        # Step 2: Validate through Meta model
        logger.info("Validating data through Meta model...")
        meta_list = loader.df_to_meta_list(df)
        logger.info("Validated %d records", len(meta_list))

        if not meta_list:
            raise CommandError("No valid records after validation")

        # Step 3: Delete ALL existing data and insert within a transaction
        logger.info("Starting database initialization (transaction)...")
        with transaction.atomic():
            # Delete existing data
            logger.info("Deleting all existing data...")
            if is_postgres:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute("TRUNCATE novels_novel_tags, novels_novel, novels_tag, novels_contest, novels_author CASCADE")
            else:
                Novel.tags.through.objects.all().delete()
                Novel.objects.all().delete()
                Tag.objects.all().delete()
                Contest.objects.all().delete()
                Author.objects.all().delete()
            logger.info("All data deleted")

            # Step 4: Create related tables
            logger.info("Creating authors...")
            authors = list({m.author for m in meta_list if m.author})
            author_count = bulk_create_ignore(
                Author, [Author(name=a) for a in progress(authors, desc="Authors")], batch_size
            )
            logger.info("Created %d authors", author_count)

            logger.info("Creating tags...")
            tags = list({t for m in meta_list for t in m.tags})
            tag_count = bulk_create_ignore(
                Tag, [Tag(name=t) for t in progress(tags, desc="Tags")], batch_size
            )
            logger.info("Created %d tags", tag_count)

            logger.info("Creating contests...")
            contests = list({m.contest for m in meta_list if m.contest})
            contest_count = bulk_create_ignore(
                Contest, [Contest(name=c) for c in progress(contests, desc="Contests")], batch_size
            )
            logger.info("Created %d contests", contest_count)

            # Step 5: Build FK mapping dictionaries
            logger.info("Building FK mappings...")
            author_map = {a.name: a.id for a in Author.objects.all()}
            contest_map = {c.name: c.id for c in Contest.objects.all()}

            # Step 6: Create Novel objects
            logger.info("Creating novels...")
            novels = []
            for meta in progress(meta_list, desc="Novels"):
                django_data = meta.to_django_dict()
                novels.append(
                    Novel(
                        id=django_data["id"],
                        title=django_data["title"],
                        author_id=author_map.get(meta.author),
                        contest_id=contest_map.get(meta.contest) if meta.contest else None,
                        genre=django_data["genre"],
                        status=django_data["status"],
                        ptype=django_data["ptype"],
                        has_banner=django_data["has_banner"],
                        word_num=django_data["word_num"],
                        click_num=django_data["click_num"],
                        praise_num=django_data["praise_num"],
                        like_num=django_data["like_num"],
                        review_num=django_data["review_num"],
                        comment_num=django_data["comment_num"],
                        cover=django_data["cover"],
                        last_update=django_data["last_update"],
                    )
                )
            novel_count = bulk_create_ignore(Novel, novels, batch_size)
            logger.info("Created %d novels", novel_count)

            # Step 7: Create M2M relationships (tags)
            logger.info("Creating novel-tag relationships...")
            tag_map = {t.name: t.id for t in Tag.objects.all()}
            novel_tags = []
            for meta in progress(meta_list, desc="Tag relations"):
                for tag_name in meta.tags:
                    if tag_name in tag_map:
                        novel_tags.append((meta.nid, tag_map[tag_name]))

            if novel_tags:
                if is_postgres:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        for i in range(0, len(novel_tags), batch_size):
                            batch = novel_tags[i:i + batch_size]
                            args_str = ",".join(
                                cursor.mogrify("(%s,%s)", (nid, tid)).decode()
                                for nid, tid in batch
                            )
                            cursor.execute(
                                f"INSERT INTO novels_novel_tags (novel_id, tag_id) VALUES {args_str} ON CONFLICT DO NOTHING"
                            )
                    m2m_count = len(novel_tags)
                else:
                    m2m_count = bulk_create_m2m(
                        Novel.tags.through,
                        [Novel.tags.through(novel_id=nid, tag_id=tid) for nid, tid in novel_tags],
                        batch_size,
                    )
            else:
                m2m_count = 0
            logger.info("Created %d novel-tag relationships", m2m_count)

            # Step 8: Load tasks if exists
            tasks_path = path.parent / "tasks.csv" if path.is_dir() else None
            if tasks_path and tasks_path.exists():
                self._load_tasks(tasks_path)

        logger.info("Database initialized successfully!")

    def _load_tasks(self, path: Path):
        """Load tasks from CSV file."""
        from novels.models import Task

        import pandas as pd

        logger.info("Loading tasks from %s", path)
        df = pd.read_csv(path)
        if df.empty:
            logger.info("No tasks to load")
            return

        tasks = []
        for _, row in progress(df.iterrows(), desc="Tasks", total=len(df)):
            tasks.append(
                Task(
                    novel_id=row["novel_id"],
                    status=row.get("status", Task.Status.DEFAULT),
                )
            )
        count = Task.objects.bulk_create(tasks, ignore_conflicts=True)
        logger.info("Created %d tasks", len(count))
