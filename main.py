"""SFACG 元数据入库 -- CLI 入口。

用法:
    uv run main.py                       遍历 output/ 全部 jsonl，insert 模式
    uv run main.py output/meta.jsonl     单文件入库，insert 模式
    uv run main.py --update              全量入库，update 模式
    uv run main.py --update output/...   单文件入库，update 模式
    uv run main.py --insert              全量入库，insert 模式（默认）

insert 模式: 假设绝大多数为新数据，新增入 bulk insert，极少量更新逐行
update 模式: 假设绝大多数为已有数据，更新走 bulk update，极少量新增逐行
"""

import sys
from pathlib import Path

from sqlmodel import SQLModel

from data_import import _process_one
from database import sqlite_engine

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"

if __name__ == "__main__":
    SQLModel.metadata.create_all(sqlite_engine)

    mode = "insert"
    if "--update" in sys.argv:
        mode = "update"
    if "--insert" in sys.argv:
        mode = "insert"

    # 收集非 --flag 的参数作为文件路径
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]

    if not paths:
        paths = sorted(OUTPUT_DIR.glob("*.jsonl"))

    if not paths:
        print("无待处理的 .jsonl 文件")
        sys.exit(0)

    all_other_nids: set[int] = set()
    for filepath in paths:
        all_other_nids.update(_process_one(filepath, mode))

    if all_other_nids:
        OTHER_FILE = ROOT / "OTHER.txt"
        with open(OTHER_FILE, "a") as f:
            for nid in sorted(all_other_nids):
                f.write(f"{nid}\n")
        print(f"OTHER 降级 {len(all_other_nids)} 条，已追加到 {OTHER_FILE}")

    print("完成")
