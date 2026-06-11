import tomllib
from pathlib import Path

_config = None

# Project root: novel_hub/ (parent of website/)
_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_config():
    global _config
    if _config is None:
        config_path = _ROOT / "site_config.toml"
        if config_path.exists():
            with open(config_path, "rb") as f:
                _config = tomllib.load(f)
        else:
            _config = {}
    return _config


def toml_config_processor(request):
    return {"TOML": _load_config()}
