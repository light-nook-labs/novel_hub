"""Task table maintenance

Usage:
    uv run python website/task_runner.py
    uv run python website/task_runner.py --limit 100
    uv run python website/task_runner.py --skip-fill

Pipeline:
1. fill_tasks — populate Task table with novels that have duplicate covers
2. run_tasks  — re-scrape each Task's novel, update DB, delete Task
"""

import argparse
import os
import sys

import django
import requests

# Add project root to path so `import scraper` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from novels.models import Task  # noqa: E402
from novels.mappings import GENRE, STATUS, PTYPE  # noqa: E402
from scraper import fetch_html, fetch_cover, fetch_api  # noqa: E402


def fill_tasks():
    """Call Django management command to populate Task table."""
    from django.core.management import call_command

    call_command("fill_tasks")


def run_tasks(limit=None, nid_min=None, nid_max=None):
    """Iterate Task table, fetch+update each novel, delete task."""
    from novels.models import Author, Contest, Tag

    session = requests.Session()
    tasks = Task.objects.select_related("novel").all()
    if nid_min is not None:
        tasks = tasks.filter(novel_id__gte=nid_min)
    if nid_max is not None:
        tasks = tasks.filter(novel_id__lte=nid_max)
    if limit:
        tasks = tasks[:limit]
    total = tasks.count() if limit is None else limit
    print(f"Processing {total} tasks ...")

    success = 0
    failed = 0
    for i, task in enumerate(tasks, 1):
        novel = task.novel
        try:
            html_data = fetch_html(session, novel.id)
            cover_url = fetch_cover(session, novel.id)
            api_data = fetch_api(session, novel.id)
            data = {**html_data, **api_data}

            # Simple scalar fields
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

            # Cover from mobile page (skip default images)
            if cover_url and "defaultNew.jpg" not in cover_url:
                novel.cover = cover_url

            # Enum strings → int
            if data.get("status"):
                novel.status = STATUS.get_value(data["status"])
            if data.get("genre"):
                novel.genre = GENRE.get_value(data["genre"])
            if data.get("ptype"):
                novel.ptype = PTYPE.get_value(data["ptype"])

            # Author FK
            author_name = data.get("author")
            if author_name:
                author, _ = Author.objects.get_or_create(name=author_name)
                novel.author = author

            # Contest FK
            contest_name = data.get("contest")
            if contest_name:
                contest, _ = Contest.objects.get_or_create(name=contest_name)
                novel.contest = contest

            novel.save()

            # Tags M2M
            tag_names = data.get("tags", [])
            if tag_names:
                tag_objs = []
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tag_objs.append(tag)
                novel.tags.set(tag_objs)

            task.delete()
            success += 1
            print(f"  [{i}/{total}] Novel {novel.id} " f"updated, task deleted")
        except Exception as e:
            failed += 1
            print(f"  [{i}/{total}] Novel {novel.id} FAILED: {e}")

    remaining = Task.objects.count()
    print(f"Done. {success} updated, {failed} failed, " f"{remaining} tasks remaining.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task table maintenance")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of tasks to process",
    )
    parser.add_argument(
        "--nid-min",
        type=int,
        default=None,
        help="Min novel ID (inclusive)",
    )
    parser.add_argument(
        "--nid-max",
        type=int,
        default=None,
        help="Max novel ID (inclusive)",
    )
    parser.add_argument(
        "--skip-fill",
        action="store_true",
        help="Skip fill_tasks step",
    )
    args = parser.parse_args()

    if not args.skip_fill:
        fill_tasks()
    run_tasks(
        limit=args.limit,
        nid_min=args.nid_min,
        nid_max=args.nid_max,
    )
