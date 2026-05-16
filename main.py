"""SFACG 元数据入库 -- CLI 入口。

用法:
    uv run main.py                       遍历 output/ 全部 jsonl
    uv run main.py path/to/file.jsonl    单文件入库

自动按 nid 区分新增（bulk insert）和更新（bulk update）。
"""

import sys
from pathlib import Path

from ingest import ingest

if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths = [Path(a) for a in sys.argv[1:]]
    else:
        paths = None

    ingest(paths, init_cloud=True)
