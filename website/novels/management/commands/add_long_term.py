"""Add novel as long-term task."""

from django.core.management.base import BaseCommand

from novels.models import Novel, Task


class Command(BaseCommand):
    help = "Add novel as long-term task"

    def add_arguments(self, parser):
        parser.add_argument("nid", type=int, help="Novel ID")

    def handle(self, *args, **options):
        nid = options["nid"]
        novel = Novel.objects.get(id=nid)

        task, created = Task.objects.update_or_create(
            novel=novel,
            defaults={"status": Task.Status.LONG_TERM},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} " f"long-term task for {nid}"
            )
        )
