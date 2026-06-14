"""Archive snapshots to JSONL and CSV files."""

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand

from novels.models import NovelSnapshot


class Command(BaseCommand):
    help = "Archive snapshots to JSONL/CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            help="Month to archive (YYYY-MM format)",
        )

    def handle(self, *args, **options):
        # Determine month
        if options["month"]:
            year, month = map(int, options["month"].split("-"))
        else:
            last_month = date.today().replace(day=1) - timedelta(days=1)
            year, month = last_month.year, last_month.month

        # Get snapshots
        snapshots = NovelSnapshot.objects.filter(
            snapshot_date__year=year,
            snapshot_date__month=month,
        ).order_by("novel_id", "snapshot_date")

        count = snapshots.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("No snapshots to archive"))
            return

        # Export both formats
        output_dir = Path("release/dataset")
        output_dir.mkdir(parents=True, exist_ok=True)

        self._export_jsonl(snapshots, year, month, output_dir)
        self._export_csv(snapshots, year, month, output_dir)

        # Delete from DB
        deleted, _ = snapshots.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Archived {count} snapshots (JSONL + CSV), "
                f"deleted {deleted} from DB"
            )
        )

    def _export_jsonl(self, snapshots, year, month, output_dir):
        jsonl_dir = output_dir / "jsonl"
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        output = jsonl_dir / f"snapshot_{year}_{month:02d}.jsonl"

        with open(output, "w", encoding="utf-8") as f:
            for s in snapshots:
                record = {
                    "nid": s.novel_id,
                    "date": s.snapshot_date.isoformat(),
                    "click_num": s.click_num,
                    "like_num": s.like_num,
                    "praise_num": s.praise_num,
                    "word_num": s.word_num,
                    "review_num": s.review_num,
                    "comment_num": s.comment_num,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self.stdout.write(f"Exported to {output}")

    def _export_csv(self, snapshots, year, month, output_dir):
        csv_dir = output_dir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        output = csv_dir / f"snapshot_{year}_{month:02d}.csv"

        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "nid",
                    "date",
                    "click_num",
                    "like_num",
                    "praise_num",
                    "word_num",
                    "review_num",
                    "comment_num",
                ]
            )
            for s in snapshots:
                writer.writerow(
                    [
                        s.novel_id,
                        s.snapshot_date,
                        s.click_num,
                        s.like_num,
                        s.praise_num,
                        s.word_num,
                        s.review_num,
                        s.comment_num,
                    ]
                )

        self.stdout.write(f"Exported to {output}")
