"""Management command to fix missing M2M tag relationships.

Queries existing novels and tags, loads source data, and rebuilds
the novel-tag M2M relationships without touching other tables.

Usage:
    uv run python manage.py fix_m2m <path>
    uv run python manage.py fix_m2m --check

Examples:
    uv run python manage.py fix_m2m ../release/dataset/
    uv run python manage.py fix_m2m ../release/dataset/meta_01.jsonl
    uv run python manage.py fix_m2m --check
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from novels.models import Novel, Tag

from utils import loader
from utils.logger import get_logger, progress

logger = get_logger(__name__)


class Command(BaseCommand):
    help = "Fix missing M2M tag relationships from source data"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            type=str,
            help="Path to JSONL file, directory containing meta_*.jsonl files, or CSV file",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Batch size for bulk operations (default: 5000)",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only check M2M status, do not fix",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        check_only = options["check"]
        force = options["force"]
        path = options.get("path")
        batch_size = options["batch_size"]

        # Detect database type
        db_type = settings.DATABASES["default"]["ENGINE"]
        is_postgres = "postgresql" in db_type

        # Check current M2M status
        novel_count = Novel.objects.count()
        tag_count = Tag.objects.count()
        m2m_count = Novel.tags.through.objects.count()

        self.stdout.write(f"Novels: {novel_count}")
        self.stdout.write(f"Tags: {tag_count}")
        self.stdout.write(f"M2M relationships: {m2m_count}")

        if novel_count == 0:
            self.stdout.write(self.style.WARNING("No novels in database. Run init_db first."))
            return

        if tag_count == 0:
            self.stdout.write(self.style.WARNING("No tags in database. Run init_db first."))
            return

        if m2m_count > 0 and check_only:
            # Show some stats
            novels_with_tags = Novel.tags.through.objects.values("novel_id").distinct().count()
            self.stdout.write(f"Novels with tags: {novels_with_tags}")
            self.stdout.write(self.style.SUCCESS("M2M relationships exist."))
            return

        if m2m_count > 0 and not check_only:
            if not force:
                confirm = input(f"M2M table has {m2m_count} entries. Rebuild? [y/N] ")
                if confirm.lower() != "y":
                    self.stdout.write("Cancelled.")
                    return

        if check_only:
            self.stdout.write(self.style.WARNING("M2M table is empty!"))
            return

        if not path:
            raise CommandError("Path is required to fix M2M relationships")

        path = Path(path)
        if not path.exists():
            raise CommandError(f"Path does not exist: {path}")

        # Load source data
        logger.info("Loading data from %s", path)
        if path.suffix == ".csv":
            df = loader.load_csv(path)
        else:
            df = loader.load_jsonl(path)
        logger.info("Loaded %d records", len(df))

        # Validate through Meta model
        logger.info("Validating data...")
        meta_list = loader.df_to_meta_list(df)
        logger.info("Validated %d records", len(meta_list))

        # Build lookup maps from existing DB data
        logger.info("Building lookup maps...")
        existing_novel_ids = set(Novel.objects.values_list("id", flat=True))
        tag_map = {t.name: t.id for t in Tag.objects.all()}

        # Build M2M pairs (only for novels and tags that exist in DB)
        novel_tags = []
        skipped_novels = 0
        skipped_tags = set()
        for meta in progress(meta_list, desc="Building M2M"):
            if meta.nid not in existing_novel_ids:
                skipped_novels += 1
                continue
            for tag_name in meta.tags:
                tag_id = tag_map.get(tag_name)
                if tag_id:
                    novel_tags.append((meta.nid, tag_id))
                else:
                    skipped_tags.add(tag_name)

        logger.info("Built %d M2M pairs (%d novels not in DB, %d tags not in DB)",
                     len(novel_tags), skipped_novels, len(skipped_tags))
        if skipped_tags:
            logger.warning("Unknown tags: %s", ", ".join(sorted(skipped_tags)[:10]))

        if not novel_tags:
            self.stdout.write(self.style.ERROR("No M2M pairs to create!"))
            return

        # Insert M2M relationships
        logger.info("Inserting M2M relationships...")
        with transaction.atomic():
            if is_postgres:
                from django.db import connection
                with connection.cursor() as cursor:
                    inserted = 0
                    for i in progress(range(0, len(novel_tags), batch_size), desc="Inserting"):
                        batch = novel_tags[i:i + batch_size]
                        args_str = ",".join(
                            cursor.mogrify("(%s,%s)", (nid, tid)).decode()
                            for nid, tid in batch
                        )
                        cursor.execute(
                            f"INSERT INTO novels_novel_tags (novel_id, tag_id) VALUES {args_str} ON CONFLICT DO NOTHING"
                        )
                        inserted += len(batch)
            else:
                from utils.loader_sqlite import bulk_create_m2m
                objs = [
                    Novel.tags.through(novel_id=nid, tag_id=tid)
                    for nid, tid in novel_tags
                ]
                inserted = bulk_create_m2m(Novel.tags.through, objs, batch_size)

        # Verify
        final_count = Novel.tags.through.objects.count()
        logger.info("Done! M2M relationships: %d → %d", m2m_count, final_count)
        self.stdout.write(self.style.SUCCESS(f"Fixed! M2M relationships: {m2m_count} → {final_count}"))
