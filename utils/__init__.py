"""utils — shared utilities for sfacg.com scraping and data processing.

Public API:
    fetch_html(session, nid) — detail page HTML → all fields
    fetch_cover(session, nid) — mobile page → cover URL
    fetch_api(session, nid)  — comment/review JSON API
    TOML — full site_config.toml dict
    Meta — shared Pydantic model for novel metadata
    GENRE, STATUS, PTYPE — enum mappings
    CHUNK_SIZE — fixed chunk size for JSONL/CSV files (20000)
    loader — pandas-based dataset processing
"""

from .api import fetch_api
from .config import TOML, COVER_PREFIX, DEFAULT_COVER, TIMEZONE
from .html import fetch_cover, fetch_html
from .loader import CHUNK_SIZE
from .mappings import GENRE, STATUS, PTYPE
from .models import Meta
from . import loader

__all__ = [
    "fetch_html",
    "fetch_cover",
    "fetch_api",
    "TOML",
    "COVER_PREFIX",
    "DEFAULT_COVER",
    "TIMEZONE",
    "GENRE",
    "STATUS",
    "PTYPE",
    "Meta",
    "CHUNK_SIZE",
    "loader",
]
