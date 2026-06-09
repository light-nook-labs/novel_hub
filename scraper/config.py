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
