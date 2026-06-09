from django.db import connection
from django.db.models import Count
from django.core.management.base import BaseCommand

from novels.models import Novel, Task

BATCH = 500


class Command(BaseCommand):
    help = "Populate Task table with novels that have duplicate cover URLs"

    def handle(self, *args, **options):
        self.stdout.write("Finding novels with duplicate covers ...")

        dupes = (
            Novel.objects.filter(cover__isnull=False)
            .exclude(cover="")
            .exclude(cover__contains="defaultNew.jpg")
            .values("cover")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )

        cover_urls = [d["cover"] for d in dupes]
        self.stdout.write(f"  {len(cover_urls)} duplicate cover URLs found")

        novel_ids = []
        for i in range(0, len(cover_urls), BATCH):
            batch = cover_urls[i : i + BATCH]
            ids = list(
                Novel.objects.filter(cover__in=batch)
                .order_by("-last_update")
                .values_list("id", flat=True)
            )
            novel_ids.extend(ids)

        self.stdout.write(f"  {len(novel_ids)} novels to insert into Task")

        self.stdout.write("Bulk creating tasks ...")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            for i in range(0, len(novel_ids), BATCH):
                batch = novel_ids[i : i + BATCH]
                cursor.executemany(
                    "INSERT OR IGNORE INTO novels_task (novel_id) VALUES (?)",
                    [(nid,) for nid in batch],
                )

        total = Task.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Done. {total} tasks in table."))
