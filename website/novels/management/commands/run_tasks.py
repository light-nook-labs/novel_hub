"""Management command to process tasks: crawl novel details, update DB.

Processes up to 500 tasks per run:
1. Fetch tasks ordered by status priority (u > d > f), novel_id desc
2. Crawl novel detail page + comment API
3. Update novel metadata in DB
4. Mark task as finished
5. Delete finished tasks after all processed

Usage:
    uv run python manage.py run_tasks [--limit 500]

Examples:
    uv run python manage.py run_tasks
    uv run python manage.py run_tasks --limit 100
"""

import requests

from django.core.management.base import BaseCommand
from django.db import transaction

from novels.models import Novel, Task
from novels.mappings import GENRE, STATUS, PTYPE

from utils import fetch_html, fetch_api, Meta
from utils.config import COVER_PREFIX, DEFAULT_COVER
from utils.logger import get_logger, progress

logger = get_logger(__name__)

# Default cover suffix → None
def _compress_cover(cover):
    if not cover:
        return None
    if cover.startswith(COVER_PREFIX):
        suffix = cover[len(COVER_PREFIX):]
        return None if suffix == DEFAULT_COVER else suffix
    return cover


class Command(BaseCommand):
    help = "Process tasks: crawl novel details, update DB, mark finished"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max tasks to process (default: 500)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        # Get tasks ordered by priority (u > d > f), novel_id desc
        tasks = Task.objects.select_related("novel")[:limit]
        total = tasks.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No tasks to process."))
            return

        logger.info("Processing %d tasks (limit: %d)", total, limit)

        session = requests.Session()
        success = 0
        failed = 0

        for task in progress(tasks, desc="Processing"):
            novel = task.novel
            nid = novel.id

            try:
                # Crawl detail page
                html_data = fetch_html(session, nid)

                # Crawl comment/review API
                api_data = fetch_api(session, nid)

                # Build Meta object for validation
                meta = Meta(
                    nid=nid,
                    title=html_data.get("title") or novel.title,
                    author=html_data.get("author") or "",
                    genre=html_data.get("genre") or "其他",
                    status=html_data.get("status") or "连载中",
                    ptype=html_data.get("ptype") or "免费",
                    has_banner=html_data.get("has_banner", False),
                    word_num=html_data.get("word_num"),
                    click_num=html_data.get("click_num"),
                    praise_num=html_data.get("praise_num"),
                    like_num=html_data.get("like_num"),
                    comment_num=api_data.get("comment_num"),
                    contest=html_data.get("contest") or "",
                    last_update=html_data.get("last_update"),
                    review_num=api_data.get("review_num"),
                    tags=html_data.get("tags", []),
                    cover=novel.cover,  # Keep existing cover
                )

                # Convert to Django dict
                django_data = meta.to_django_dict()

                # Update novel
                with transaction.atomic():
                    for field, value in django_data.items():
                        if field in ("id", "tags"):
                            continue  # Skip PK and M2M
                        if value is not None:
                            setattr(novel, field, value)
                    novel.save()

                    # Mark task as finished
                    task.status = Task.Status.FINISHED
                    task.save()

                success += 1

            except Exception as e:
                logger.error("Failed to process task %d (novel %d): %s", task.id, nid, e)
                failed += 1

        # Delete finished tasks
        deleted, _ = Task.objects.filter(status=Task.Status.FINISHED).delete()
        logger.info("Deleted %d finished tasks", deleted)

        # Summary
        remaining = Task.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done! Processed: {success}, Failed: {failed}, "
            f"Deleted: {deleted}, Remaining: {remaining}"
        ))
