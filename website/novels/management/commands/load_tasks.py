"""Load tasks.csv into Task table."""

import csv
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from novels.models import Task


class Command(BaseCommand):
    help = "Load tasks.csv into Task table"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="../release/tasks.csv",
            help="Path to tasks.csv (default: ../release/tasks.csv)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete all existing tasks before loading",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        path = Path(options["path"])

        if not path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        if not options["force"]:
            self.stderr.write(
                self.style.ERROR("Refusing to delete all tasks without --force")
            )
            return

        self.stdout.write(f"Loading tasks from {path} ...")
        Task.objects.all().delete()

        batch = []
        total = 0
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                batch.append(Task(novel_id=int(row["novel_id"]), status=row["status"]))
                if len(batch) >= 5000:
                    Task.objects.bulk_create(batch, ignore_conflicts=True)
                    total += len(batch)
                    batch = []

        if batch:
            Task.objects.bulk_create(batch, ignore_conflicts=True)
            total += len(batch)

        elapsed = time.time() - t0
        self.stdout.write(
            self.style.SUCCESS(f"Done in {elapsed:.1f}s — {total} tasks loaded")
        )
