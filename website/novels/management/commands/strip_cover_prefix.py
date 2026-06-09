from django.core.management.base import BaseCommand
from novels.models import Novel

PREFIX = "http://rs.sfacg.com/web/novel/images/NovelCover/Big/"


class Command(BaseCommand):
    help = "Strip cover URL prefix, keep suffix only"

    def handle(self, *args, **options):
        self.stdout.write("Stripping cover prefix ...")

        novels = Novel.objects.filter(cover__startswith=PREFIX)
        count = novels.count()
        self.stdout.write(f"  {count} novels with full URL prefix")

        batch = []
        for novel in novels.iterator():
            novel.cover = novel.cover[len(PREFIX) :]
            batch.append(novel)
            if len(batch) >= 5000:
                Novel.objects.bulk_update(batch, ["cover"])
                batch = []

        if batch:
            Novel.objects.bulk_update(batch, ["cover"])

        self.stdout.write(self.style.SUCCESS(f"Done. {count} covers updated."))
