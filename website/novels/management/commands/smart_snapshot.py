"""Create daily snapshots of ON_GOING novels and long-term tasks."""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from novels.models import Novel, NovelSnapshot


class Command(BaseCommand):
    help = "Create daily snapshots"

    def handle(self, *args, **options):
        today = date.today()

        # 1. ON_GOING novels updated within 7 days
        week_ago = today - timedelta(days=7)
        ongoing = Novel.objects.filter(
            status=3,  # ON_GOING
            last_update__date__gte=week_ago,
        )

        # 2. Long-term tasks
        long_term = Novel.objects.filter(task__status="l")

        # 3. Merge and deduplicate
        novels = (ongoing | long_term).distinct()

        # 4. Bulk create snapshots
        snapshots = []
        for novel in novels:
            snapshots.append(
                NovelSnapshot(
                    novel=novel,
                    snapshot_date=today,
                    click_num=novel.click_num,
                    like_num=novel.like_num,
                    praise_num=novel.praise_num,
                    word_num=novel.word_num,
                    review_num=novel.review_num,
                    comment_num=novel.comment_num,
                )
            )

        if snapshots:
            NovelSnapshot.objects.bulk_create(snapshots, ignore_conflicts=True)

        # 5. Delete snapshots older than 30 days
        cutoff = today - timedelta(days=30)
        deleted, _ = NovelSnapshot.objects.filter(snapshot_date__lt=cutoff).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(snapshots)} snapshots, deleted {deleted} old"
            )
        )
