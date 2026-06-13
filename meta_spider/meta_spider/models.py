"""Re-export shared Pydantic models from project root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.models import Meta

__all__ = ["Meta"]
