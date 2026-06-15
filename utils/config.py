"""Shared config — reads from site_config.toml."""

import logging
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_config_path = _ROOT / "site_config.toml"

if _config_path.exists():
    with open(_config_path, "rb") as f:
        TOML = tomllib.load(f)
else:
    TOML = {}
    logger.warning("site_config.toml not found at %s, using defaults", _config_path)

_cfg = TOML.get("urls", {})
_site = TOML.get("site", {})

USER_AGENT = _cfg.get("user_agent", "")
HEADERS = {"User-Agent": USER_AGENT}
COMMON_URL = _cfg.get("common", "")
NOVEL_URL = _cfg.get("novel", "https://book.sfacg.com/Novel/{nid}/")
MOBILE_URL = _cfg.get("mobile", "https://m.sfacg.com/b/{nid}/")
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
}
COVER_PREFIX = _cfg.get(
    "cover_prefix",
    "http://rs.sfacg.com/web/novel/images/NovelCover/Big/",
)
DEFAULT_COVER = _cfg.get("default_cover", "defaultNew.jpg")
TIMEZONE = _site.get("timezone", "Asia/Shanghai")
