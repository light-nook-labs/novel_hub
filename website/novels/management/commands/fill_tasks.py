"""Management command to populate Task table with duplicate-cover novels.

Finds novels sharing the same cover (excluding None), creates Task entries.
Priority: URGENT for has_banner=True or active status, DEFAULT otherwise.

Usage:
    uv run python manage.py fill_tasks [--dry-run]

Examples:
    uv run python manage.py fill_tasks
    uv run python manage.py fill_tasks --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from novels.models import Novel, Task
from novels.mappings import STATUS

from utils.logger import get_logger, progress

logger = get_logger(__name__)

# Status values
ACTIVE_D = STATUS.enum.ACTIVE_D.value  # 断更A
ACTIVE_F = STATUS.enum.ACTIVE_F.value  # 完结A
DIED = STATUS.enum.DIED.value  # 断更
FINISHED = STATUS.enum.FINISHED.value  # 已完结


class Command(BaseCommand):
    help = "Populate Task table with duplicate-cover novels"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show results without creating tasks",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Step 1: Find covers that appear more than once (excluding None)
        logger.info("Finding duplicate covers...")
        duplicate_covers = (
            Novel.objects.filter(cover__isnull=False)
            .exclude(cover="")
            .values("cover")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .values_list("cover", flat=True)
        )
        duplicate_covers = list(duplicate_covers)
        logger.info("Found %d duplicate covers", len(duplicate_covers))

        if not duplicate_covers:
            self.stdout.write(self.style.SUCCESS("No duplicate covers found."))
            return

        # Step 2: Get all novels with duplicate covers (batch for SQLite)
        logger.info("Fetching novels with duplicate covers...")
        novels = []
        batch_size = 500
        for i in range(0, len(duplicate_covers), batch_size):
            batch = duplicate_covers[i : i + batch_size]
            novels.extend(Novel.objects.filter(cover__in=batch).select_related("task"))
        total = len(novels)
        logger.info("Found %d novels with duplicate covers", total)

        # Step 3: Classify and create tasks
        urgent_novels = []
        default_novels = []

        def _is_active_candidate(n):
            """Check if novel meets A-status criteria."""
            return (
                n.has_banner
                or (n.click_num or 0) >= 10_000_000
                or (n.review_num or 0) >= 60
                or (n.like_num or 0) >= 10_000
                or (n.praise_num or 0) >= 10_000
            )

        for novel in progress(novels, desc="Classifying"):
            # Skip if task already exists
            if hasattr(novel, "task") and novel.task is not None:
                continue

            # Determine priority
            is_urgent = False

            # Already A-status → urgent
            if novel.status in (ACTIVE_D, ACTIVE_F):
                is_urgent = True
            # Meets A-status criteria → urgent (regardless of status)
            elif _is_active_candidate(novel):
                is_urgent = True

            if is_urgent:
                urgent_novels.append(novel)
            else:
                default_novels.append(novel)

        logger.info(
            "Classification: %d urgent, %d default",
            len(urgent_novels),
            len(default_novels),
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no tasks created"))
            self.stdout.write(f"  Urgent: {len(urgent_novels)}")
            self.stdout.write(f"  Default: {len(default_novels)}")
            self.stdout.write(f"  Total: {len(urgent_novels) + len(default_novels)}")
            return

        # Step 4: Create tasks in bulk
        with transaction.atomic():
            tasks = []
            for novel in urgent_novels:
                tasks.append(Task(novel_id=novel.id, status=Task.Status.URGENT))
            for novel in default_novels:
                tasks.append(Task(novel_id=novel.id, status=Task.Status.DEFAULT))

            created = Task.objects.bulk_create(tasks, ignore_conflicts=True)
            logger.info("Created %d tasks", len(created))

        # Summary
        total_tasks = Task.objects.count()
        urgent_count = Task.objects.filter(status=Task.Status.URGENT).count()
        default_count = Task.objects.filter(status=Task.Status.DEFAULT).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Tasks: {total_tasks} (urgent: {urgent_count}, default: {default_count})"
            )
        )
