"""Management command to dump database to JSONL/CSV format.

Usage:
    uv run python manage.py dump_dataset <output_path> [--format jsonl|csv]

Examples:
    uv run python manage.py dump_dataset release
    uv run python manage.py dump_dataset release --format csv
    uv run python manage.py dump_dataset release/dataset --format jsonl
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from novels.models import Novel, Task

from utils import loader
from utils.logger import get_logger, progress
from utils.models import Meta

logger = get_logger(__name__)


class Command(BaseCommand):
    help = "Dump database to JSONL/CSV format"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_path",
            type=str,
            help="Output directory path",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["jsonl", "csv"],
            default="jsonl",
            help="Output format (default: jsonl)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output_path"])
        output_format = options["format"]
        chunk_size = loader.CHUNK_SIZE

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Load all tags into memory (small dataset)
        logger.info("Loading tags...")
        novel_tags = Novel.tags.through.objects.values("novel_id", "tag__name")
        tags_dict = {}
        for nt in novel_tags:
            tags_dict.setdefault(nt["novel_id"], []).append(nt["tag__name"])
        logger.info("Loaded tags for %d novels", len(tags_dict))

        # Step 2: Query novels in batches and convert to Meta objects
        logger.info("Querying novels...")
        novel_qs = Novel.objects.values(
            "id", "title", "author__name", "genre", "status", "ptype",
            "has_banner", "word_num", "click_num", "praise_num", "like_num",
            "review_num", "comment_num", "contest__name", "last_update", "cover",
        )
        total = novel_qs.count()
        logger.info("Total novels: %d", total)

        meta_list = []
        batch_size = 10000
        for start in progress(range(0, total, batch_size), desc="Converting"):
            for row in novel_qs[start:start + batch_size]:
                try:
                    meta = Meta.from_django_dict(row)
                    meta.tags = tags_dict.get(meta.nid, [])
                    meta_list.append(meta)
                except Exception as e:
                    logger.debug("Validation error for id=%s: %s", row.get("id"), e)

        logger.info("Converted %d novels", len(meta_list))

        # Step 3: Output files
        if output_format == "jsonl":
            self._dump_jsonl(meta_list, output_path, chunk_size)
        else:
            self._dump_csv(meta_list, output_path)

        # Step 4: Dump tasks
        self._dump_tasks(output_path)

        logger.info("Dataset dumped successfully!")

    def _dump_jsonl(self, meta_list: list[Meta], output_path: Path, chunk_size: int):
        """Dump Meta objects to JSONL files."""
        import json

        total = len(meta_list)
        if total == 0:
            logger.warning("No data to dump")
            return

        # Split into chunks
        num_files = (total + chunk_size - 1) // chunk_size
        for i in range(num_files):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, total)
            chunk = meta_list[start:end]

            filename = f"meta_{i + 1:02d}.jsonl"
            filepath = output_path / filename

            with open(filepath, "w", encoding="utf-8") as f:
                for meta in progress(chunk, desc=f"Writing {filename}"):
                    record = meta.model_dump()
                    # Convert datetime to string for JSON serialization
                    if record.get("last_update"):
                        record["last_update"] = record["last_update"].isoformat()
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            logger.info("Written %s: %d records", filepath, len(chunk))

    def _dump_csv(self, meta_list: list[Meta], output_path: Path):
        """Dump Meta objects to CSV file."""
        import pandas as pd

        filepath = output_path / "dataset.csv"
        records = [meta.model_dump() for meta in progress(meta_list, desc="Writing CSV")]
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info("Written %s: %d records", filepath, len(meta_list))

    def _dump_tasks(self, output_path: Path):
        """Dump tasks to CSV file."""
        import pandas as pd

        tasks = Task.objects.values("novel_id", "status")
        if not tasks.exists():
            logger.info("No tasks to dump")
            return

        df = pd.DataFrame(list(tasks))
        filepath = output_path / "tasks.csv"
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info("Written %s: %d tasks", filepath, len(df))
