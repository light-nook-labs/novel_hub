from pathlib import Path

from reset_db import reset
from ingest import ingest


p = Path("output/")

if __name__ == '__main__':
    reset()
    ingest(p.iterdir())