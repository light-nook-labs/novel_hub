"""Common constants and utility functions."""

import pandas as pd
from django.conf import settings
from datetime import timedelta

from novels.mappings import GENRE, STATUS, PTYPE

# ── Column definitions (no side effects) ────────────────────────────

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

# ── Mapping dicts (lazily computed) ─────────────────────────────────

_GENRE_MAP = None
_STATUS_MAP = None
_PTYPE_MAP = None
_GENRE_FALLBACK = None
_STATUS_FALLBACK = None
_PTYPE_FALLBACK = None
_DIED_THRESHOLD = None


def _lazy_init():
    """Lazily initialize mapping dicts (called on first access)."""
    global _GENRE_MAP, _STATUS_MAP, _PTYPE_MAP
    global _GENRE_FALLBACK, _STATUS_FALLBACK, _PTYPE_FALLBACK, _DIED_THRESHOLD
    if _GENRE_MAP is not None:
        return
    _GENRE_MAP = GENRE.zh_to_value_dict()
    _STATUS_MAP = STATUS.zh_to_value_dict()
    _PTYPE_MAP = PTYPE.zh_to_value_dict()
    _GENRE_FALLBACK = GENRE.fallback()
    _STATUS_FALLBACK = STATUS.fallback()
    _PTYPE_FALLBACK = PTYPE.fallback()
    _DIED_THRESHOLD = timedelta(
        days=settings.TOML.get("thresholds", {}).get("died_days", 90)
    )


def get_genre_map():
    _lazy_init()
    return _GENRE_MAP


def get_status_map():
    _lazy_init()
    return _STATUS_MAP


def get_ptype_map():
    _lazy_init()
    return _PTYPE_MAP


def get_genre_fallback():
    _lazy_init()
    return _GENRE_FALLBACK


def get_status_fallback():
    _lazy_init()
    return _STATUS_FALLBACK


def get_ptype_fallback():
    _lazy_init()
    return _PTYPE_FALLBACK


def get_died_threshold():
    _lazy_init()
    return _DIED_THRESHOLD


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
    if isinstance(val, bool):
        return int(val)
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def is_na(val):
    """Check if value is NA/None/NaN."""
    return pd.isna(val)
