"""Shared task loading utilities."""

import csv
import time

from novels.models import Task


def load_tasks_from_csv(path, stdout, force=False):
    """Load tasks.csv into Task table.

    Args:
        path: Path to tasks.csv or directory containing it.
        stdout: Command stdout for logging.
        force: If False, skip loading.
    """
    if not path.is_dir():
        return
    if not force:
        stdout.write("  Tasks: skipped (use --force)")
        return

    tasks_file = path / "tasks.csv"
    if not tasks_file.exists():
        tasks_file = path.parent / "tasks.csv"
    if not tasks_file.exists():
        stdout.write("  tasks.csv not found")
        return

    t_step = time.perf_counter()
    batch = []
    total = 0
    Task.objects.all().delete()

    with open(tasks_file) as f:
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

    elapsed = time.perf_counter() - t_step
    stdout.write(f"  Tasks loaded: {total} records ({elapsed:.2f}s)")
