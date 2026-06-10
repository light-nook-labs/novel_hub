import json
import sys
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from novels.models import Novel, Tag
from novels.mappings import GENRE, STATUS, PTYPE

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent.parent)
)
from models import Meta  # noqa: E402

RECORDS_PER_FILE = 20_000


class Command(BaseCommand):
    help = "Dump database to JSONL files (20k records each) for release"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="dataset/release",
            help="Output directory (default: dataset/release)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Queryset chunk size for memory efficiency (default: 2000)",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        out_dir = Path(options["path"])
        out_dir.mkdir(parents=True, exist_ok=True)
        batch_size = options["batch_size"]

        from config.toml import _load_config

        config = _load_config()
        cover_prefix = config["scraper"]["cover_prefix"]

        total = Novel.objects.count()
        self.stdout.write(f"Dumping {total} novels to {out_dir}/")

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
                out_path = out_dir / f"meta_{file_idx:02d}.jsonl"
                self.stdout.write(f"  writing {out_path} ...")
                out_file = open(out_path, "w", encoding="utf-8")
                record_idx = 0

            cover = cover_prefix + novel.cover if novel.cover else ""

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
                self.stderr.write(
                    f"  validation error for novel {novel.id}: {e}"
                )
                errors += 1
                continue

            line = json.dumps(meta.to_jsonl_dict(), ensure_ascii=False)
            out_file.write(line + "\n")
            record_idx += 1

        if out_file:
            out_file.close()

        elapsed = time.time() - t0
        msg = f"Done in {elapsed:.1f}s — {total} novels → {file_idx} files"
        if errors:
            msg += f" ({errors} validation errors skipped)"
        self.stdout.write(self.style.SUCCESS(msg))
