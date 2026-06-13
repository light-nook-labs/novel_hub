"""Task table maintenance: fill tasks + re-scrape each novel.

Usage:
    uv run python manage.py run_tasks
    uv run python manage.py run_tasks --limit 100
    uv run python manage.py run_tasks --skip-fill
    uv run python manage.py run_tasks --status u
    uv run python manage.py run_tasks --nid-min 1000 --nid-max 2000
"""

import logging
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import models

from novels.models import Task
from novels.mappings import GENRE, STATUS, PTYPE

# Add project root so `import scraper` works
_project_root = str(settings.BASE_DIR.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fill tasks and re-scrape each novel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None, help="Max tasks to process"
        )
        parser.add_argument(
            "--nid-min", type=int, default=None, help="Min novel ID (inclusive)"
        )
        parser.add_argument(
            "--nid-max", type=int, default=None, help="Max novel ID (inclusive)"
        )
        parser.add_argument(
            "--skip-fill", action="store_true", help="Skip fill_tasks step"
        )
        parser.add_argument(
            "--status",
            choices=[c[0] for c in Task.Status.choices],
            default=None,
            help="Filter tasks by status (u=urgent, d=default, f=finished)",
        )

    def handle(self, *args, **options):
        if not options["skip_fill"]:
            self.stdout.write("Filling tasks ...")
            call_command("fill_tasks")

        self._run_tasks(
            limit=options["limit"],
            nid_min=options["nid_min"],
            nid_max=options["nid_max"],
            status=options["status"],
        )

    def _run_tasks(self, limit=None, nid_min=None, nid_max=None, status=None):
        """Iterate Task table, fetch+update each novel, mark finished."""
        import requests
        from novels.models import Author, Contest, Tag
        from scraper import fetch_html, fetch_cover, fetch_api

        session = requests.Session()
        tasks = Task.objects.select_related("novel").exclude(
            status=Task.Status.FINISHED
        )
        if status:
            tasks = tasks.filter(status=status)
        else:
            tasks = tasks.order_by(
                models.Case(
                    models.When(status=Task.Status.URGENT, then=0),
                    default=1,
                ),
                "-novel__last_update",
            )
        if nid_min is not None:
            tasks = tasks.filter(novel_id__gte=nid_min)
        if nid_max is not None:
            tasks = tasks.filter(novel_id__lte=nid_max)
        if limit:
            tasks = tasks[:limit]
        total = tasks.count() if limit is None else limit
        self.stdout.write(f"Processing {total} tasks ...")

        success = 0
        failed = 0
        finished_ids = []
        for i, task in enumerate(tasks, 1):
            novel = task.novel
            try:
                html_data = fetch_html(session, novel.id)
                cover_url = fetch_cover(session, novel.id)
                api_data = fetch_api(session, novel.id)
                data = {**html_data, **api_data}

                for key in [
                    "title",
                    "word_num",
                    "click_num",
                    "praise_num",
                    "like_num",
                    "has_banner",
                    "last_update",
                    "comment_num",
                    "review_num",
                ]:
                    val = data.get(key)
                    if val is not None:
                        setattr(novel, key, val)

                if cover_url and "defaultNew.jpg" not in cover_url:
                    novel.cover = cover_url

                if data.get("status"):
                    novel.status = STATUS.get_value(data["status"])
                if data.get("genre"):
                    novel.genre = GENRE.get_value(data["genre"])
                if data.get("ptype"):
                    novel.ptype = PTYPE.get_value(data["ptype"])

                author_name = data.get("author")
                if author_name:
                    author, _ = Author.objects.get_or_create(name=author_name)
                    novel.author = author

                contest_name = data.get("contest")
                if contest_name:
                    contest, _ = Contest.objects.get_or_create(name=contest_name)
                    novel.contest = contest

                novel.save()

                tag_names = data.get("tags", [])
                if tag_names:
                    tag_objs = []
                    for name in tag_names:
                        tag, _ = Tag.objects.get_or_create(name=name)
                        tag_objs.append(tag)
                    novel.tags.set(tag_objs)

                finished_ids.append(task.id)
                success += 1
            except Exception as e:
                failed += 1
                logger.warning("[%d/%d] Novel %d FAILED: %s", i, total, novel.id, e)

        if finished_ids:
            deleted, _ = Task.objects.filter(id__in=finished_ids).delete()
            self.stdout.write(f"  Deleted {deleted} finished tasks")

        remaining = Task.objects.exclude(status=Task.Status.FINISHED).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {success} updated, {failed} failed, {remaining} remaining."
            )
        )
