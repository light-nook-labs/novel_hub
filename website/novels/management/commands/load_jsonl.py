import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from django.db import connection
from django.core.management.base import BaseCommand

from novels.models import Novel, Author, Tag, Contest
from novels.mappings import GENRE, STATUS, PTYPE

DIED_THRESHOLD = timedelta(days=90)

GENRE_ZH2VAL = {zh: GENRE.get_value(zh) for zh in GENRE._zh_en}
STATUS_ZH2VAL = {zh: STATUS.get_value(zh) for zh in STATUS._zh_en}
PTYPE_ZH2VAL = {zh: PTYPE.get_value(zh) for zh in PTYPE._zh_en}

GENRE_FALLBACK = GENRE.enum.OTHER.value
STATUS_FALLBACK = STATUS.enum.OTHER.value
PTYPE_FALLBACK = PTYPE.enum.OTHER.value


def _get_cover_prefix():
    """Read cover_prefix from site_config.toml."""
    from config.toml import _load_config

    config = _load_config()
    return config.get("scraper", {}).get("cover_prefix", "")


def _int_or_zero(val):
    if pd.isna(val):
        return None
    return int(val)


def _clean_cover(url, cover_prefix):
    if pd.isna(url):
        return None
    if not url or url == "nan":
        return None
    if "defaultNew.jpg" in url:
        return None
    # Remove prefix (possibly doubled from bad dumps)
    while cover_prefix and url.startswith(cover_prefix):
        url = url[len(cover_prefix):]
    return url


def _clean_title(row):
    """Strip ptype and contest name from title if appended."""
    title = row.novel_title
    contest = row.contest
    ptype = row.price_type
    if pd.isna(title):
        return title, ptype

    ptype_str = ptype.strip() if not pd.isna(ptype) else ""

    # Strip contest first (it's at the end)
    if not pd.isna(contest):
        contest = contest.strip()
        if contest and title.endswith(contest):
            title = title[: -len(contest)].rstrip()

    # Strip VIP/签约 from title and fix ptype if needed
    if title.endswith("VIP"):
        title = title[:-3].rstrip()
        ptype = "VIP"
    elif title.endswith("签约"):
        title = title[:-2].rstrip()
        ptype = "签约"
    elif ptype_str and title.endswith(ptype_str):
        title = title[: -len(ptype_str)].rstrip()

    return title, ptype


def load_and_clean(files: list[Path], cover_prefix: str) -> pd.DataFrame:
    frames = []
    for f in files:
        frames.append(pd.read_json(f, lines=True, dtype_backend="numpy_nullable"))
    df = pd.concat(frames, ignore_index=True)

    text_cols = ["author", "contest", "cover", "novel_title"]
    exist_text = [c for c in text_cols if c in df.columns]
    if exist_text:
        df[exist_text] = df[exist_text].astype("string").replace("", pd.NA)

    if "author" in df.columns:
        df["author"] = df["author"].str.strip().str.replace(r"\s+", " ", regex=True)

    df["last_update"] = pd.to_datetime(df["last_update"], unit="ms", errors="coerce")

    df = df.loc[df.groupby("nid")["last_update"].idxmax()].reset_index(drop=True)

    df["genre"] = df["genre"].map(GENRE_ZH2VAL).fillna(GENRE_FALLBACK).astype("Int64")
    df["status"] = (
        df["status"].map(STATUS_ZH2VAL).fillna(STATUS_FALLBACK).astype("Int64")
    )
    df["ptype"] = (
        df["price_type"].map(PTYPE_ZH2VAL).fillna(PTYPE_FALLBACK).astype("Int64")
    )

    df["cover"] = df["cover"].apply(lambda x: _clean_cover(x, cover_prefix))
    # pandas stores None as NaN in float columns; cast to object first so where gives real None
    df["cover"] = df["cover"].astype(object).where(df["cover"].notna(), other=None)

    if "contest" in df.columns:
        df[["novel_title", "price_type"]] = df.apply(
            _clean_title, axis=1, result_type="expand"
        )
        # Re-map ptype after cleaning
        df["ptype"] = (
            df["price_type"].map(PTYPE_ZH2VAL).fillna(PTYPE_FALLBACK).astype("Int64")
        )

    int_cols = [
        "word_num",
        "click_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
    ]
    for col in int_cols:
        if col not in df.columns:
            df[col] = pd.NA
    df[int_cols] = df[int_cols].apply(pd.to_numeric, errors="coerce").astype("Int64")

    now = datetime.now()
    died_cutoff = now - DIED_THRESHOLD
    on_going_mask = (df["status"] == STATUS.enum.ON_GOING.value) & (
        df["last_update"] < died_cutoff
    )
    df.loc[on_going_mask, "status"] = STATUS.enum.DIED.value

    active_mask = (
        df["banner"].fillna(False).eq(True)
        | df["click_num"].fillna(0).ge(10_000_000)
        | df["praise_num"].fillna(0).ge(10_000)
        | df["like_num"].fillna(0).ge(10_000)
        | df["review_num"].fillna(0).ge(80)
    )
    df.loc[
        active_mask & (df["status"] == STATUS.enum.DIED.value),
        "status",
    ] = STATUS.enum.ACTIVE_D.value
    df.loc[
        active_mask & (df["status"] == STATUS.enum.FINISHED.value),
        "status",
    ] = STATUS.enum.ACTIVE_F.value

    return df


class Command(BaseCommand):
    help = "Load novel data from JSONL files (pandas cleaning, fast bulk insert)"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="dataset/data",
            help="JSONL file or directory (default: dataset/data)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of records to load (0 = no limit)",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        path = Path(options["path"])
        limit = options["limit"]

        if path.is_dir():
            files = sorted(path.glob("*.jsonl"))
        else:
            files = [path]

        if not files:
            self.stderr.write(self.style.ERROR(f"No JSONL files found at {path}"))
            return

        # Read cover_prefix from site_config.toml
        cover_prefix = _get_cover_prefix()
        self.stdout.write(f"Cover prefix: {cover_prefix}")

        self.stdout.write(f"Loading {len(files)} files from {path} ...")
        t_step = time.time()
        df = load_and_clean(files, cover_prefix)

        # Apply limit if specified
        if limit > 0:
            df = df.head(limit)
            self.stdout.write(f"  Limited to {limit} records")

        self.stdout.write(
            f"  pandas cleaning: {time.time() - t_step:.1f}s — {len(df)} novels after dedup"
        )

        authors = df["author"].dropna().unique().tolist()
        contests = df["contest"].dropna().unique().tolist()
        tag_lists = df["tags"].dropna().tolist()
        all_tags = list({t for tags in tag_lists for t in tags if t})
        self.stdout.write(
            f"  unique: {len(authors)} authors, {len(contests)} contests, {len(all_tags)} tags"
        )

        BATCH = 5000

        t_step = time.time()
        Author.objects.bulk_create(
            [Author(name=a) for a in authors], batch_size=BATCH, ignore_conflicts=True
        )
        author_map = {a.name: a.id for a in Author.objects.all()}
        self.stdout.write(f"  authors: {time.time() - t_step:.1f}s")

        t_step = time.time()
        Contest.objects.bulk_create(
            [Contest(name=c) for c in contests],
            batch_size=BATCH,
            ignore_conflicts=True,
        )
        contest_map = {c.name: c.id for c in Contest.objects.all()}
        self.stdout.write(f"  contests: {time.time() - t_step:.1f}s")

        t_step = time.time()
        Tag.objects.bulk_create(
            [Tag(name=t) for t in all_tags], batch_size=BATCH, ignore_conflicts=True
        )
        tag_map = {t.name: t.id for t in Tag.objects.all()}
        self.stdout.write(f"  tags: {time.time() - t_step:.1f}s")

        t_step = time.time()
        novel_objs = []
        for row in df.itertuples(index=False):
            novel_objs.append(
                Novel(
                    id=row.nid,
                    title=row.novel_title if pd.notna(row.novel_title) else "",
                    ptype=row.ptype,
                    genre=row.genre,
                    status=row.status,
                    click_num=_int_or_zero(row.click_num),
                    word_num=_int_or_zero(row.word_num),
                    praise_num=_int_or_zero(row.praise_num),
                    like_num=_int_or_zero(row.like_num),
                    review_num=_int_or_zero(getattr(row, "review_num", 0)),
                    comment_num=_int_or_zero(getattr(row, "comment_num", 0)),
                    has_banner=bool(row.banner) if pd.notna(row.banner) else False,
                    cover=row.cover,
                    last_update=row.last_update if pd.notna(row.last_update) else None,
                    author_id=(
                        author_map.get(row.author) if pd.notna(row.author) else None
                    ),
                    contest_id=(
                        contest_map.get(row.contest) if pd.notna(row.contest) else None
                    ),
                )
            )
        Novel.objects.bulk_create(novel_objs, batch_size=BATCH, ignore_conflicts=True)
        del novel_objs

        self.stdout.write("  updating statuses via raw SQL ...")
        status_rows = [
            (int(row.status), int(row.nid))
            for row in df[["nid", "status"]].itertuples(index=False)
            if pd.notna(row.status)
        ]
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.executemany(
                    "UPDATE novels_novel SET status = %s WHERE id = %s",
                    status_rows,
                )
            else:
                cursor.executemany(
                    "UPDATE novels_novel SET status = ? WHERE id = ?",
                    status_rows,
                )
        self.stdout.write(f"  novels: {time.time() - t_step:.1f}s")

        t_step = time.time()
        tag_rows = []
        for row in df[["nid", "tags"]].dropna(subset=["tags"]).itertuples(index=False):
            nid = int(row.nid)
            for t in row.tags:
                tid = tag_map.get(t)
                if tid is not None:
                    tag_rows.append((nid, int(tid)))

        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.executemany(
                    "INSERT INTO novels_novel_tags (novel_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    tag_rows,
                )
            else:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=OFF")
                cursor.executemany(
                    "INSERT OR IGNORE INTO novels_novel_tags (novel_id, tag_id) VALUES (?, ?)",
                    tag_rows,
                )
                cursor.execute("PRAGMA foreign_keys=ON")
        self.stdout.write(f"  M2M tags: {time.time() - t_step:.1f}s")

        total = time.time() - t0
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {total:.1f}s — "
                f"{len(df)} novels, {len(authors)} authors, "
                f"{len(contests)} contests, {len(all_tags)} tags, "
                f"{len(tag_rows)} tag links"
            )
        )
