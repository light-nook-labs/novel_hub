"""Export database to release directory.

Creates release/ with jsonl/, csv/, and tasks.csv.

Usage:
    uv run python manage.py dump_dataset
    uv run python manage.py dump_dataset --output ../release
"""

import csv
import json
import sys
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from novels.models import Novel, Tag, Task
from novels.mappings import GENRE, STATUS, PTYPE

sys.path.insert(0, str(settings.BASE_DIR.parent))
from models import Meta  # noqa: E402

RECORDS_PER_FILE = 20_000


class Command(BaseCommand):
    help = "Export database to release/ (jsonl/ + csv/ + tasks.csv)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="release",
            help="Output directory (default: release)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Queryset chunk size (default: 2000)",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        out_dir = Path(options["output"])
        batch_size = options["batch_size"]

        cover_prefix = settings.TOML["scraper"]["cover_prefix"]

        novels = self._load_novels(batch_size)

        self._dump_jsonl(out_dir, novels, cover_prefix)
        self._dump_csv(out_dir, cover_prefix)
        self._dump_tasks(out_dir)

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.1f}s"))

    def _load_novels(self, batch_size):
        """Load all novels with relations."""
        tag_prefetch = Prefetch("tags", queryset=Tag.objects.only("name"))
        return list(
            Novel.objects.select_related("author", "contest")
            .prefetch_related(tag_prefetch)
            .only(
                "id",
                "title",
                "ptype",
                "genre",
                "status",
                "click_num",
                "word_num",
                "praise_num",
                "like_num",
                "review_num",
                "comment_num",
                "has_banner",
                "cover",
                "last_update",
                "author__name",
                "contest__name",
            )
            .order_by("id")
            .iterator(chunk_size=batch_size)
        )

    def _build_meta(self, novel, cover_prefix):
        """Build Meta model from novel object."""
        cover = novel.cover
        if not cover or cover in ("nan", "<NA>"):
            cover = cover_prefix + "defaultNew.jpg"
        else:
            cover = cover_prefix + cover

        title = novel.title
        contest_name = novel.contest.name if novel.contest else ""
        ptype_name = PTYPE.get_zh(novel.ptype)

        if contest_name and title.endswith(contest_name):
            title = title[: -len(contest_name)].rstrip()

        if title.endswith("VIP"):
            title = title[:-3].rstrip()
            ptype_name = "VIP"
        elif title.endswith("签约"):
            title = title[:-2].rstrip()
            ptype_name = "签约"
        elif ptype_name and title.endswith(ptype_name):
            title = title[: -len(ptype_name)].rstrip()

        return Meta(
            nid=novel.id,
            title=title,
            author=novel.author.name if novel.author else "",
            genre=GENRE.get_zh(novel.genre),
            status=STATUS.get_zh(novel.status),
            has_banner=novel.has_banner,
            word_num=novel.word_num,
            click_num=novel.click_num,
            praise_num=novel.praise_num,
            like_num=novel.like_num,
            ptype=ptype_name,
            contest=contest_name,
            last_update=novel.last_update,
            review_num=novel.review_num,
            comment_num=novel.comment_num,
            tags=[t.name for t in novel.tags.all()],
            cover=cover,
        )

    def _dump_jsonl(self, out_dir, novels, cover_prefix):
        """Export novels as JSONL files."""
        jsonl_dir = out_dir / "jsonl"
        jsonl_dir.mkdir(parents=True, exist_ok=True)

        total = len(novels)
        self.stdout.write(f"JSONL: {total} novels → {jsonl_dir}/")

        file_idx = 0
        record_idx = 0
        out_file = None
        errors = 0

        for novel in novels:
            if record_idx % RECORDS_PER_FILE == 0:
                if out_file:
                    out_file.close()
                file_idx += 1
                out_path = jsonl_dir / f"meta_{file_idx:02d}.jsonl"
                self.stdout.write(f"  writing {out_path} ...")
                out_file = open(out_path, "w", encoding="utf-8")
                record_idx = 0

            try:
                meta = self._build_meta(novel, cover_prefix)
            except Exception as e:
                self.stderr.write(f"  validation error for novel {novel.id}: {e}")
                errors += 1
                continue

            line = json.dumps(meta.model_dump(), ensure_ascii=False, default=str)
            out_file.write(line + "\n")
            record_idx += 1

        if out_file:
            out_file.close()

        msg = f"  {total} novels → {file_idx} files"
        if errors:
            msg += f" ({errors} errors)"
        self.stdout.write(msg)

    def _dump_csv(self, out_dir, cover_prefix):
        """Export novels as CSV files."""
        csv_dir = out_dir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)

        total = Novel.objects.count()
        self.stdout.write(f"CSV: {total} novels → {csv_dir}/")

        fields = list(Meta.model_fields.keys())
        file_idx = 0
        record_idx = 0
        out_file = None
        writer = None
        errors = 0

        tag_prefetch = Prefetch("tags", queryset=Tag.objects.only("name"))
        novels = (
            Novel.objects.select_related("author", "contest")
            .prefetch_related(tag_prefetch)
            .only(
                "id",
                "title",
                "ptype",
                "genre",
                "status",
                "click_num",
                "word_num",
                "praise_num",
                "like_num",
                "review_num",
                "comment_num",
                "has_banner",
                "cover",
                "last_update",
                "author__name",
                "contest__name",
            )
            .order_by("id")
            .iterator(chunk_size=2000)
        )

        for novel in novels:
            if record_idx % RECORDS_PER_FILE == 0:
                if out_file:
                    out_file.close()
                file_idx += 1
                out_path = csv_dir / f"meta_{file_idx:02d}.csv"
                self.stdout.write(f"  writing {out_path} ...")
                out_file = open(out_path, "w", newline="", encoding="utf-8")
                writer = csv.DictWriter(out_file, fieldnames=fields)
                writer.writeheader()
                record_idx = 0

            try:
                meta = self._build_meta(novel, cover_prefix)
            except Exception as e:
                errors += 1
                continue

            row = meta.model_dump()
            row["tags"] = json.dumps(row["tags"], ensure_ascii=False)
            row["last_update"] = (
                row["last_update"].isoformat() if row["last_update"] else ""
            )
            writer.writerow(row)
            record_idx += 1

        if out_file:
            out_file.close()

        msg = f"  {total} novels → {file_idx} files"
        if errors:
            msg += f" ({errors} errors)"
        self.stdout.write(msg)

    def _dump_tasks(self, out_dir):
        """Export tasks as CSV."""
        out_path = out_dir / "tasks.csv"
        tasks = Task.objects.select_related("novel").only("id", "status", "novel__id")
        total = tasks.count()
        self.stdout.write(f"Tasks: {total} → {out_path}")

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "novel_id", "status"])
            for task in tasks.iterator(chunk_size=2000):
                writer.writerow([task.id, task.novel_id, task.status])

        self.stdout.write(f"  {total} tasks written")
