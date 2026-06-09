"""scraper — requests-based HTTP client for sfacg.com.

Public API:
    fetch_html(session, nid) — detail page HTML → all fields
    fetch_cover(session, nid) — mobile page → cover URL
    fetch_api(session, nid)  — comment/review JSON API
"""

from .api import fetch_api
from .html import fetch_cover, fetch_html

__all__ = ["fetch_html", "fetch_cover", "fetch_api"]
