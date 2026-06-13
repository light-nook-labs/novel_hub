"""Pandas data processing utilities."""

import pandas as pd
from django.utils import timezone

from . import (
    DIED_THRESHOLD,
    GENRE_MAP,
    STATUS_MAP,
    PTYPE_MAP,
    GENRE_FALLBACK,
    STATUS_FALLBACK,
    PTYPE_FALLBACK,
    get_timezone,
    int_or_none,
)
from novels.mappings import STATUS


def extract_entities(files, limit=0):
    """First pass: pandas read, extract unique authors, contests, tags."""
    frames = []
    remaining = limit
    for f in files:
        chunk = pd.read_json(f, lines=True, dtype_backend="numpy_nullable")
        chunk = chunk[["author", "contest", "tags"]]
        if limit > 0:
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)
            remaining -= len(chunk)
        frames.append(chunk)
    df = pd.concat(frames, ignore_index=True)
    del frames

    authors = df["author"].dropna().drop_duplicates().tolist()
    contests = df["contest"].dropna().drop_duplicates().tolist()
    tag_series = df["tags"].dropna().explode()
    tags = tag_series.dropna().drop_duplicates().tolist()

    del df
    return authors, contests, tags


def load_novels(files, cover_prefix, author_map, contest_map, tag_map, limit=0):
    """Second pass: load and clean novel data with FK resolution."""
    timezone_str = get_timezone()

    frames = []
    remaining = limit
    for f in files:
        chunk = pd.read_json(f, lines=True, dtype_backend="numpy_nullable")
        if limit > 0:
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)
            remaining -= len(chunk)
        frames.append(chunk)
    df = pd.concat(frames, ignore_index=True)
    del frames

    keep_cols = [
        "nid",
        "novel_title",
        "author",
        "genre",
        "status",
        "price_type",
        "click_num",
        "word_num",
        "praise_num",
        "like_num",
        "review_num",
        "comment_num",
        "banner",
        "cover",
        "last_update",
        "contest",
        "tags",
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    df["last_update"] = pd.to_datetime(
        df["last_update"], unit="ms", utc=True, errors="coerce"
    ).dt.tz_convert(timezone_str)

    df = df.loc[df.groupby("nid")["last_update"].idxmax()].reset_index(drop=True)

    df["genre"] = df["genre"].map(GENRE_MAP).fillna(GENRE_FALLBACK).astype("int16")
    df["status"] = df["status"].map(STATUS_MAP).fillna(STATUS_FALLBACK).astype("int16")
    df["ptype"] = df["price_type"].map(PTYPE_MAP).fillna(PTYPE_FALLBACK).astype("int16")
    df.drop(columns=["price_type"], inplace=True)

    df["cover"] = _clean_cover(df["cover"], cover_prefix)

    if "contest" in df.columns:
        df = _clean_title(df)

    df["novel_title"] = df["novel_title"].astype("category")

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
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int32")

    df["banner"] = df["banner"].fillna(False).astype("bool")

    df = _update_status(df, timezone_str)

    df["author_id"] = df["author"].map(author_map).astype("Int64")
    df["contest_id"] = df["contest"].map(contest_map).astype("Int64")

    tag_rows = _build_tag_rows(df, tag_map)

    return df, tag_rows


def build_novel_rows(df):
    """Build novel rows for database insertion."""
    now_iso = timezone.now().isoformat()
    novel_rows = []
    for row in df.itertuples(index=False):
        novel_rows.append(
            (
                int(row.nid),
                row.novel_title if pd.notna(row.novel_title) else "",
                int(row.ptype),
                int(row.genre),
                int(row.status),
                int_or_none(row.click_num),
                int_or_none(row.word_num),
                int_or_none(row.praise_num),
                int_or_none(row.like_num),
                int_or_none(getattr(row, "review_num", 0)),
                int_or_none(getattr(row, "comment_num", 0)),
                bool(row.banner),
                row.cover,
                row.last_update.isoformat() if pd.notna(row.last_update) else None,
                now_iso,
                int(row.author_id) if pd.notna(row.author_id) else None,
                int(row.contest_id) if pd.notna(row.contest_id) else None,
            )
        )
    return novel_rows


# ── Private helpers ─────────────────────────────────────────────────


def _clean_cover(cover_series, cover_prefix):
    """Vectorized cover cleaning."""
    if "defaultNew.jpg" in cover_prefix:
        return pd.Series(pd.NA, index=cover_series.index, dtype="category")
    mask_default = cover_series.str.contains("defaultNew.jpg", na=False)
    cover_series = cover_series.copy()
    cover_series[mask_default] = pd.NA
    if cover_prefix:
        cover_series = cover_series.str.removeprefix(cover_prefix)
    return cover_series.astype("category")


def _clean_title(df):
    """Vectorized title cleaning."""
    contest_mask = df["contest"].notna()
    if contest_mask.any():
        df.loc[contest_mask, "novel_title"] = df.loc[contest_mask].apply(
            lambda r: (
                r.novel_title[: -len(str(r.contest).strip())].rstrip()
                if r.novel_title.endswith(str(r.contest).strip())
                else r.novel_title
            ),
            axis=1,
        )
    title = df["novel_title"]
    vip_mask = title.str.endswith("VIP", na=False)
    df.loc[vip_mask, "novel_title"] = title.str[:-3].str.rstrip()
    qianyue_mask = title.str.endswith("签约", na=False)
    df.loc[qianyue_mask, "novel_title"] = title.str[:-2].str.rstrip()
    return df


def _update_status(df, timezone_str):
    """Vectorized status updates (died/active detection)."""
    from django.utils import timezone as tz

    now = tz.now()
    died_cutoff = pd.Timestamp(now - DIED_THRESHOLD).tz_convert(timezone_str)

    on_going_mask = (df["status"] == STATUS.enum.ON_GOING.value) & (
        df["last_update"] < died_cutoff
    )
    df.loc[on_going_mask, "status"] = STATUS.enum.DIED.value

    from django.conf import settings

    _t = settings.TOML.get("thresholds", {})
    active_mask = (
        df["banner"]
        | df["click_num"].fillna(0).ge(_t.get("active_click", 10_000_000))
        | df["praise_num"].fillna(0).ge(_t.get("active_praise", 10_000))
        | df["like_num"].fillna(0).ge(_t.get("active_like", 10_000))
        | df["review_num"].fillna(0).ge(_t.get("active_review", 80))
    )
    df.loc[active_mask & (df["status"] == STATUS.enum.DIED.value), "status"] = (
        STATUS.enum.ACTIVE_D.value
    )
    df.loc[active_mask & (df["status"] == STATUS.enum.FINISHED.value), "status"] = (
        STATUS.enum.ACTIVE_F.value
    )

    return df


def _build_tag_rows(df, tag_map):
    """Build M2M tag rows (deduplicated via pandas)."""
    tag_df = df[["nid", "tags"]].explode("tags")
    tag_df = tag_df.dropna(subset=["tags"])
    tag_df["tag_id"] = tag_df["tags"].map(tag_map)
    tag_df = tag_df.dropna(subset=["tag_id"])
    tag_df["nid"] = tag_df["nid"].astype(int)
    tag_df["tag_id"] = tag_df["tag_id"].astype(int)
    tag_df = tag_df.drop_duplicates(subset=["nid", "tag_id"])
    return list(tag_df[["nid", "tag_id"]].itertuples(index=False, name=None))
