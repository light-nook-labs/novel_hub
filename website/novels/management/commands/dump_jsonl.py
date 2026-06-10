import csv
import json
import sys
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from novels.models import Novel, Tag, Task
from novels.mappings import GENRE, STATUS, PTYPE

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))
from models import Meta  # noqa: E402

RECORDS_PER_FILE = 20_000


class Command(BaseCommand):
    help = "Dump database to release/ (dataset/*.jsonl + tasks.csv)"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
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
        out_dir = Path(options["path"])
        batch_size = options["batch_size"]

        from config.toml import _load_config

        config = _load_config()
        cover_prefix = config["scraper"]["cover_prefix"]

        self._dump_novels(out_dir, cover_prefix, batch_size)
        self._dump_tasks(out_dir)

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.1f}s"))

    def _dump_novels(self, out_dir, cover_prefix, batch_size):
        dataset_dir = out_dir / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        total = Novel.objects.count()
        self.stdout.write(f"Dumping {total} novels to {dataset_dir}/")

        file_idx = 0
        record_idx = 0
        out_file = None
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
            .iterator(chunk_size=batch_size)
        )

        for novel in novels:
            if record_idx % RECORDS_PER_FILE == 0:
                if out_file:
                    out_file.close()
                file_idx += 1
                out_path = dataset_dir / f"meta_{file_idx:02d}.jsonl"
                self.stdout.write(f"  writing {out_path} ...")
                out_file = open(out_path, "w", encoding="utf-8")
                record_idx = 0

            cover = novel.cover
            if not cover or cover == "nan":
                cover = cover_prefix + "defaultNew.jpg"
            else:
                cover = cover_prefix + cover

            try:
                meta = Meta(
                    nid=novel.id,
                    title=novel.title,
                    author=novel.author.name if novel.author else "",
                    genre=GENRE.get_zh(novel.genre),
                    status=STATUS.get_zh(novel.status),
                    has_banner=novel.has_banner,
                    word_num=novel.word_num,
                    click_num=novel.click_num,
                    praise_num=novel.praise_num,
                    like_num=novel.like_num,
                    ptype=PTYPE.get_zh(novel.ptype),
                    contest=novel.contest.name if novel.contest else "",
                    last_update=novel.last_update,
                    review_num=novel.review_num,
                    comment_num=novel.comment_num,
                    tags=[t.name for t in novel.tags.all()],
                    cover=cover,
                )
            except Exception as e:
                self.stderr.write(f"  validation error for novel {novel.id}: {e}")
                errors += 1
                continue

            line = json.dumps(meta.to_jsonl_dict(), ensure_ascii=False)
            out_file.write(line + "\n")
            record_idx += 1

        if out_file:
            out_file.close()

        msg = f"  {total} novels → {file_idx} files"
        if errors:
            msg += f" ({errors} validation errors skipped)"
        self.stdout.write(msg)

    def _dump_tasks(self, out_dir):
        out_path = out_dir / "tasks.csv"
        tasks = Task.objects.select_related("novel").only("id", "status", "novel__id")
        total = tasks.count()
        self.stdout.write(f"Dumping {total} tasks to {out_path}")

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "novel_id", "status"])
            for task in tasks.iterator(chunk_size=2000):
                writer.writerow([task.id, task.novel_id, task.status])

        self.stdout.write(f"  {total} tasks written")
