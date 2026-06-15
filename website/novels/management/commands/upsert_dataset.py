"""Management command to upsert dataset from JSONL/CSV into database.

Unlike load_dataset (INSERT OR IGNORE), this command updates existing records.

Usage:
    uv run python manage.py upsert_dataset <path>

Examples:
    uv run python manage.py upsert_dataset ../release/dataset/
    uv run python manage.py upsert_dataset ../release/dataset/meta_01.jsonl
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

# Fields to update on conflict
NOVEL_UPDATE_FIELDS = [
    "title",
    "author_id",
    "contest_id",
    "genre",
    "status",
    "ptype",
    "has_banner",
    "word_num",
    "click_num",
    "praise_num",
    "like_num",
    "review_num",
    "comment_num",
    "cover",
    "last_update",
    "db_update",
]


class Command(BaseCommand):
    help = (
        "Upsert dataset from JSONL/CSV files into database (updates existing records)"
    )

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
        parser.add_argument(
            "--skip-novels",
            action="store_true",
            help="Skip novel upsert (only update related tables)",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        batch_size = options["batch_size"]
        skip_novels = options["skip_novels"]

        if not path.exists():
            raise CommandError(f"Path does not exist: {path}")

        # Detect database type
        db_type = settings.DATABASES["default"]["ENGINE"]
        is_postgres = "postgresql" in db_type

        if is_postgres:
            from utils.loader_postgres import bulk_create_ignore, bulk_upsert
        else:
            from utils.loader_sqlite import bulk_create_ignore, bulk_upsert

        # Step 1: Load and validate data through Meta
        logger.info("Loading data from %s", path)
        if path.suffix == ".csv":
            df = loader.load_csv(path)
        else:
            df = loader.load_jsonl(path)
        logger.info("Loaded %d records", len(df))

        # Step 2: Validate through Meta model
        logger.info("Validating data through Meta model...")
        meta_list = loader.df_to_meta_list(df)
        logger.info("Validated %d records", len(meta_list))

        # Step 3: Extract and create related tables
        logger.info("Upserting authors...")
        authors = list({m.author for m in meta_list if m.author})
        author_count = bulk_create_ignore(
            Author,
            [Author(name=a) for a in progress(authors, desc="Authors")],
            batch_size,
        )
        logger.info("Created %d new authors", author_count)

        logger.info("Upserting tags...")
        tags = list({t for m in meta_list for t in m.tags if not t.startswith("[")})
        tag_count = bulk_create_ignore(
            Tag, [Tag(name=t) for t in progress(tags, desc="Tags")], batch_size
        )
        logger.info("Created %d new tags", tag_count)

        logger.info("Upserting contests...")
        contests = list({m.contest for m in meta_list if m.contest})
        contest_count = bulk_create_ignore(
            Contest,
            [Contest(name=c) for c in progress(contests, desc="Contests")],
            batch_size,
        )
        logger.info("Created %d new contests", contest_count)

        # Step 4: Build FK mapping dictionaries
        logger.info("Building FK mappings...")
        author_map = {a.name: a.id for a in Author.objects.all()}
        contest_map = {c.name: c.id for c in Contest.objects.all()}

        # Step 5: Upsert Novel objects
        if not skip_novels:
            logger.info("Upserting novels...")
            from django.utils import timezone

            now = timezone.now()
            novels = []
            for meta in progress(meta_list, desc="Novels"):
                django_data = meta.to_django_dict()
                novels.append(
                    Novel(
                        id=django_data["id"],
                        title=django_data["title"],
                        author_id=author_map.get(meta.author),
                        contest_id=(
                            contest_map.get(meta.contest) if meta.contest else None
                        ),
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
                        db_update=now,
                    )
                )
            novel_count = bulk_upsert(Novel, novels, NOVEL_UPDATE_FIELDS, batch_size)
            logger.info("Upserted %d novels", novel_count)

        # Step 6: Upsert M2M relationships (tags)
        logger.info("Upserting novel-tag relationships...")
        tag_map = {t.name: t.id for t in Tag.objects.all()}

        # Build M2M pairs
        novel_ids = [m.nid for m in meta_list]
        novel_tags = []
        for meta in progress(meta_list, desc="Tag relations"):
            for tag_name in meta.tags:
                if tag_name.startswith("["):
                    continue
                if tag_name in tag_map:
                    novel_tags.append((meta.nid, tag_map[tag_name]))

        # Delete and re-insert M2M relationships in a transaction
        with transaction.atomic():
            deleted_count, _ = Novel.tags.through.objects.filter(
                novel_id__in=novel_ids
            ).delete()
            logger.info("Deleted %d stale novel-tag relationships", deleted_count)

            if novel_tags:
                if is_postgres:
                    from django.db import connection

                    with connection.cursor() as cursor:
                        for i in range(0, len(novel_tags), batch_size):
                            batch = novel_tags[i : i + batch_size]
                            args_str = ",".join(
                                cursor.mogrify("(%s,%s)", (nid, tid)).decode()
                                for nid, tid in batch
                            )
                            cursor.execute(
                                f"INSERT INTO novels_novel_tags (novel_id, tag_id) VALUES {args_str} ON CONFLICT DO NOTHING"
                            )
                    m2m_count = len(novel_tags)
                else:
                    m2m_count = bulk_create_ignore(
                        Novel.tags.through,
                        [
                            Novel.tags.through(novel_id=nid, tag_id=tid)
                            for nid, tid in novel_tags
                        ],
                        batch_size,
                    )
            else:
                m2m_count = 0
            logger.info("Created %d new novel-tag relationships", m2m_count)

        logger.info("Dataset upserted successfully!")
