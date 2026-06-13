"""utils — shared utilities for sfacg.com scraping and data processing.

Public API:
    fetch_html(session, nid) — detail page HTML → all fields
    fetch_cover(session, nid) — mobile page → cover URL
    fetch_api(session, nid)  — comment/review JSON API
    TOML — full site_config.toml dict
    Meta — shared Pydantic model for novel metadata
"""

from .api import fetch_api
from .config import TOML
from .html import fetch_cover, fetch_html
from .models import Meta

__all__ = ["fetch_html", "fetch_cover", "fetch_api", "TOML", "Meta"]
