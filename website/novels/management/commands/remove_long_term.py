"""Remove novel from long-term tasks."""

from django.core.management.base import BaseCommand

from novels.models import Task


class Command(BaseCommand):
    help = "Remove novel from long-term tasks"

    def add_arguments(self, parser):
        parser.add_argument("nid", type=int, nargs="?", help="Novel ID")
        parser.add_argument(
            "--all", action="store_true", help="Remove all long-term tasks"
        )

    def handle(self, *args, **options):
        if options["all"]:
            deleted, _ = Task.objects.filter(status=Task.Status.LONG_TERM).delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} long-term tasks"))
        elif options["nid"]:
            nid = options["nid"]
            deleted, _ = Task.objects.filter(
                novel_id=nid, status=Task.Status.LONG_TERM
            ).delete()
            if deleted:
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted long-term task for {nid}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"No long-term task found for {nid}")
                )
        else:
            self.stdout.write(self.style.ERROR("Please provide nid or use --all"))
