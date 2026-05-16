"""SFACG 元数据入库 -- CLI 入口。

用法:
    uv run main.py                       遍历 output/ 全部 jsonl
    uv run main.py path/to/file.jsonl    单文件入库

自动按 nid 区分新增（bulk insert）和更新（bulk update）。
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

from database.cleaner import load_and_clean
from database.cloud import _sync_to_cloud
from database.engine import cloud_engine, sqlite_engine
from database.app import create_db_and_table
from database.writer import commit_dataframe

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
    log_lines: list[str] = []

    # Phase 1: 并行加载清洗
    print(f"并行加载 {len(paths)} 个文件 …", flush=True)
    t_load0 = time.perf_counter()
    with ThreadPoolExecutor() as pool:
        dfs = list(pool.map(load_and_clean, paths))
    t_load = time.perf_counter() - t_load0
    print(f"加载完成 | {t_load:.1f}s")

    # Phase 2: 顺序写入 SQLite
    known_nids: set[int] = set()
    all_other_nids: set[int] = set()
    total_inserted, total_updated = 0, 0

    for filepath, df in zip(paths, dfs):
        t_write0 = time.perf_counter()
        inserted, updated, other_nids = commit_dataframe(
            df, known_nids=known_nids
        )
        t_write = time.perf_counter() - t_write0

        total_inserted += inserted
        total_updated += updated
        all_other_nids.update(other_nids)
        print(
            f"  {filepath.name}: {len(df)} 行 | +{inserted} ~{updated} | {t_write:.1f}s"
        )
        log_lines.append(
            f"{datetime.now():%Y-%m-%d %H:%M:%S} | {filepath.name} | SQLite | "
            f"rows={len(df)} ins={inserted} upd={updated} "
            f"other={len(other_nids)} | {t_write:.1f}s"
        )

    # Phase 3: 一次性同步云端
    t_cloud0 = time.perf_counter()
    if dfs:
        cloud_df = pd.concat(dfs, ignore_index=True)
        cloud_ins, cloud_upd = _sync_to_cloud(cloud_df)
    else:
        cloud_ins, cloud_upd = 0, 0
    t_cloud = time.perf_counter() - t_cloud0
    print(f"cloud sync: +{cloud_ins} ~{cloud_upd} | {t_cloud:.1f}s")

    total_elapsed = time.perf_counter() - t_total
    log_lines.append(
        f"{datetime.now():%Y-%m-%d %H:%M:%S} | ALL | Cloud Sync | "
        f"ins={cloud_ins} upd={cloud_upd} | {t_cloud:.1f}s"
    )
    log_lines.append(
        f"{datetime.now():%Y-%m-%d %H:%M:%S} | TOTAL | "
        f"files={len(paths)} ins={total_inserted} upd={total_updated} "
        f"other={len(all_other_nids)} | {total_elapsed:.1f}s"
    )
    print(
        f"总计: 新增 {total_inserted} | 更新 {total_updated} | {total_elapsed:.1f}s"
    )

    LOG_FILE = ROOT / f"LOG_{datetime.now():%Y-%m-%d}.txt"
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
