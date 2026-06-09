"""Shared scraper config — reads from site_config.toml."""

import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_config_path = _ROOT / "site_config.toml"

with open(_config_path, "rb") as f:
    _cfg = tomllib.load(f).get("scraper", {})

USER_AGENT = _cfg.get("user_agent", "")
HEADERS = {"User-Agent": USER_AGENT}
COMMON_URL = _cfg.get("common_url", "")
NOVEL_URL = _cfg.get("novel_url", "https://book.sfacg.com/Novel/{nid}/")
MOBILE_URL = _cfg.get("mobile_url", "https://m.sfacg.com/b/{nid}/")
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
}
COVER_PREFIX = "http://rs.sfacg.com/web/novel/images/NovelCover/Big/"
