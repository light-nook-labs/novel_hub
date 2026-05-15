"""SFACG 元数据入库 -- CLI 入口。

用法:
    uv run main.py                       遍历 output/ 全部 jsonl
    uv run main.py path/to/file.jsonl    单文件入库

自动按 nid 区分新增（bulk insert）和更新（bulk update）。
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from database import cloud_engine, sqlite_engine
from database.app import create_db_and_table
from ingest import _process_one

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"

if __name__ == "__main__":
    create_db_and_table(sqlite_engine)
    if cloud_engine is not None:
        create_db_and_table(cloud_engine)

    if len(sys.argv) > 1:
        paths = [Path(a) for a in sys.argv[1:]]
    else:
        paths = sorted(OUTPUT_DIR.glob("*.jsonl"))

    if not paths:
        print("无待处理的 .jsonl 文件")
        sys.exit(0)

    t_total = time.perf_counter()
    all_other_nids: set[int] = set()
    total_inserted, total_updated = 0, 0
    log_lines: list[str] = []

    for filepath in paths:
        info = _process_one(filepath)
        total_inserted += info["inserted"]
        total_updated += info["updated"]
        all_other_nids.update(info["other_nids"])
        log_lines.append(
            f"{datetime.now():%Y-%m-%d %H:%M:%S} | {info['file']} | "
            f"rows={info['rows']} ins={info['inserted']} upd={info['updated']} "
            f"other={info['other']} | {info['elapsed']:.1f}s"
        )

    total_elapsed = time.perf_counter() - t_total
    summary = (
        f"{datetime.now():%Y-%m-%d %H:%M:%S} | TOTAL | "
        f"files={len(paths)} rows=N/A ins={total_inserted} upd={total_updated} "
        f"other={len(all_other_nids)} | {total_elapsed:.1f}s"
    )
    log_lines.append(summary)
    print(f"总计: 新增 {total_inserted} | 更新 {total_updated} | {total_elapsed:.1f}s")

    # 写入 LOG.txt
    LOG_FILE = ROOT / "LOG.txt"
    with open(LOG_FILE, "a") as f:
        for line in log_lines:
            f.write(line + "\n")

    if all_other_nids:
        OTHER_FILE = ROOT / "OTHER.txt"
        with open(OTHER_FILE, "a") as f:
            for nid in sorted(all_other_nids):
                f.write(f"{nid}\n")
        print(f"OTHER 降级 {len(all_other_nids)} 条 -> {OTHER_FILE}")

    print(f"日志 -> {LOG_FILE}")
    print("完成")
