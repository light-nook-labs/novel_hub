"""Common constants and utility functions."""

import pandas as pd
from django.conf import settings
from datetime import timedelta

from novels.mappings import GENRE, STATUS, PTYPE

# ── Constants from mappings ─────────────────────────────────────────

DIED_THRESHOLD = timedelta(
    days=settings.TOML.get("thresholds", {}).get("died_days", 90)
)

GENRE_MAP = GENRE.zh_to_value_dict()
STATUS_MAP = STATUS.zh_to_value_dict()
PTYPE_MAP = PTYPE.zh_to_value_dict()

GENRE_FALLBACK = GENRE.fallback()
STATUS_FALLBACK = STATUS.fallback()
PTYPE_FALLBACK = PTYPE.fallback()

NOVEL_COLUMNS = (
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
    "db_update",
    "author_id",
    "contest_id",
)

NOVEL_UPDATE_COLUMNS = (
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
    "db_update",
    "author_id",
    "contest_id",
)


# ── Utility functions ───────────────────────────────────────────────


def get_cover_prefix():
    """Read cover_prefix from TOML config."""
    return settings.TOML.get("scraper", {}).get("cover_prefix", "")


def get_timezone():
    """Read timezone from TOML config."""
    return settings.TOML.get("scraper", {}).get("timezone", "Asia/Shanghai")


def int_or_none(val):
    """Convert value to int or None."""
    if pd.isna(val):
        return None
    return int(val)


def is_na(val):
    """Check if value is NA/None/NaN."""
    return pd.isna(val)
