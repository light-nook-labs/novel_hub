"""Management command to create release dataset tar archive.

Creates a tar archive containing:
- csv/: CSV files with 20k records each
- jsonl/: JSONL files with 20k records each
- tasks.csv: Task table export

Usage:
    uv run python manage.py create_release --output ../release.tar.gz

Examples:
    uv run python manage.py create_release
    uv run python manage.py create_release --output release_v1.0.tar.gz
"""

import csv
import io
import tarfile
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import F

from novels.models import Novel, Task
from utils.config import COVER_PREFIX, DEFAULT_COVER
from utils.logger import get_logger, progress

logger = get_logger(__name__)

CHUNK_SIZE = 20000


class Command(BaseCommand):
    help = "Create release dataset tar archive"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="../release.tar.gz",
            help="Output tar file path (default: ../release.tar.gz)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])

        # Fetch all novels using iterator to avoid SQLite limits
        logger.info("Fetching novels...")
        novels = []
        for novel in (
            Novel.objects.select_related("author", "contest")
            .prefetch_related("tags")
            .order_by("id")
            .iterator(chunk_size=2000)
        ):
            # Force prefetch by accessing tags
            _ = list(novel.tags.all())
            novels.append(novel)
        total_novels = len(novels)
        logger.info("Fetched %d novels", total_novels)

        # Fetch all tasks
        logger.info("Fetching tasks...")
        tasks = list(
            Task.objects.select_related("novel")
            .order_by("novel_id")
            .iterator(chunk_size=2000)
        )
        total_tasks = len(tasks)
        logger.info("Fetched %d tasks", total_tasks)

        # Create tar archive
        logger.info("Creating tar archive: %s", output_path)
        with tarfile.open(output_path, "w:gz") as tar:
            # Add JSONL files
            self._add_jsonl_files(tar, novels)

            # Add CSV files
            self._add_csv_files(tar, novels)

            # Add tasks.csv
            self._add_tasks_csv(tar, tasks)

        logger.info("Release archive created: %s", output_path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Archive: {output_path} "
                f"({total_novels} novels, {total_tasks} tasks)"
            )
        )

    def _novel_to_dict(self, novel):
        """Convert Novel instance to dict for export."""
        # Reconstruct full cover URL
        cover = novel.cover
        if cover:
            if not cover.startswith("http"):
                cover = COVER_PREFIX + cover
        else:
            cover = COVER_PREFIX + DEFAULT_COVER

        # Format last_update with timezone
        last_update = None
        if novel.last_update:
            last_update = novel.last_update.isoformat()
            if not last_update.endswith("+00:00"):
                last_update += "+00:00"

        return {
            "nid": novel.id,
            "title": novel.title,
            "author": novel.author.name if novel.author else "",
            "genre": novel.get_genre_display(),
            "status": novel.get_status_display(),
            "has_banner": novel.has_banner,
            "word_num": novel.word_num,
            "click_num": novel.click_num,
            "praise_num": novel.praise_num,
            "like_num": novel.like_num,
            "ptype": novel.get_ptype_display(),
            "contest": novel.contest.name if novel.contest else None,
            "last_update": last_update,
            "review_num": novel.review_num,
            "comment_num": novel.comment_num,
            "tags": [tag.name for tag in novel.tags.all()],
            "cover": cover,
        }

    def _add_jsonl_files(self, tar, novels):
        """Add JSONL files to tar archive."""
        import json

        logger.info("Generating JSONL files...")
        total = len(novels)
        file_idx = 1

        for start in range(0, total, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, total)
            chunk = novels[start:end]

            # Generate JSONL content
            lines = []
            for novel in progress(chunk, desc=f"JSONL {file_idx:02d}"):
                data = self._novel_to_dict(novel)
                lines.append(json.dumps(data, ensure_ascii=False))

            content = "\n".join(lines) + "\n"
            filename = f"jsonl/meta_{file_idx:02d}.jsonl"

            # Add to tar
            info = tarfile.TarInfo(name=filename)
            info.size = len(content.encode("utf-8"))
            tar.addfile(info, io.BytesIO(content.encode("utf-8")))

            logger.info("Added %s (%d records)", filename, len(chunk))
            file_idx += 1

    def _add_csv_files(self, tar, novels):
        """Add CSV files to tar archive."""
        logger.info("Generating CSV files...")
        total = len(novels)
        file_idx = 1

        for start in range(0, total, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, total)
            chunk = novels[start:end]

            # Generate CSV content
            output = io.StringIO()
            writer = None

            for novel in progress(chunk, desc=f"CSV {file_idx:02d}"):
                data = self._novel_to_dict(novel)
                # Convert list fields to strings for CSV
                data["tags"] = "|".join(data["tags"]) if data["tags"] else ""

                if writer is None:
                    writer = csv.DictWriter(output, fieldnames=data.keys())
                    writer.writeheader()

                writer.writerow(data)

            content = output.getvalue()
            filename = f"csv/meta_{file_idx:02d}.csv"

            # Add to tar
            info = tarfile.TarInfo(name=filename)
            info.size = len(content.encode("utf-8"))
            tar.addfile(info, io.BytesIO(content.encode("utf-8")))

            logger.info("Added %s (%d records)", filename, len(chunk))
            file_idx += 1

    def _add_tasks_csv(self, tar, tasks):
        """Add tasks.csv to tar archive."""
        logger.info("Generating tasks.csv...")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["novel_id", "status", "novel_title"])

        for task in tasks:
            writer.writerow(
                [
                    task.novel_id,
                    task.get_status_display(),
                    task.novel.title if task.novel else "",
                ]
            )

        content = output.getvalue()

        info = tarfile.TarInfo(name="tasks.csv")
        info.size = len(content.encode("utf-8"))
        tar.addfile(info, io.BytesIO(content.encode("utf-8")))

        logger.info("Added tasks.csv (%d records)", len(tasks))
