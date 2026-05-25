"""SFACG 小说元数据入库工具。

三阶段流水线：并行加载清洗 -> 顺序写入 SQLite -> 同步云端。
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from database.app import create_db_and_table
from old.cleaner import load_and_clean
from old.cloud import _sync_to_cloud
from database.engine import cloud_engine, sqlite_engine
from old.writer import commit_dataframe

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"


def ingest(
    paths: "Sequence[Path] | None" = None,
    *,
    init_cloud: bool = True,
) -> tuple[int, int, int]:
    """执行元数据入库流程。

    Args:
        paths: 待处理的 jsonl 文件路径列表，None 则遍历 output/ 目录
        init_cloud: 是否在开始时初始化云端数据库表（main 风格），
                    False 则延迟到 Phase 3 前初始化（旧 ingest 风格）

    Returns:
        (total_inserted, total_updated, other_nids_count)
    """
    if paths is None:
        paths = sorted(OUTPUT_DIR.glob("*.jsonl"))
    else:
        paths = list(paths)

    if not paths:
        print("无待处理的 .jsonl 文件")
        return 0, 0, 0

    create_db_and_table(sqlite_engine)
    if init_cloud and cloud_engine is not None:
        create_db_and_table(cloud_engine)

    t_total = time.perf_counter()
    log_lines: list[str] = []

    # Phase 1: 并行加载清洗
    def _safe_load(filepath):
        try:
            return load_and_clean(filepath)
        except Exception as e:
            print(f"  [ERROR] {filepath.name}: {e}", flush=True)
            return None

    print(f"并行加载 {len(paths)} 个文件 ...", flush=True)
    t_load0 = time.perf_counter()
    with ThreadPoolExecutor() as pool:
        dfs = list(pool.map(_safe_load, paths))
    t_load = time.perf_counter() - t_load0
    print(f"加载完成 | {t_load:.1f}s")

    # 过滤加载失败的文件
    valid_paths = []
    valid_dfs = []
    for filepath, df in zip(paths, dfs):
        if df is not None:
            valid_paths.append(filepath)
            valid_dfs.append(df)
    paths = valid_paths
    dfs = valid_dfs

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
    if not init_cloud and cloud_engine is not None:
        create_db_and_table(cloud_engine)
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

    # 写入 LOG.txt
    LOG_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOG_DIR / f"LOG_{datetime.now():%Y-%m-%d}.txt"
    with open(LOG_FILE, "a") as f:
        for line in log_lines:
            f.write(line + "\n")

    if all_other_nids:
        OTHER_FILE = ROOT / "OTHER.txt"
        if OTHER_FILE.exists():
            with open(OTHER_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_other_nids.add(int(line))
        with open(OTHER_FILE, "w") as f:
            for nid in sorted(all_other_nids):
                f.write(f"{nid}\n")
        print(f"OTHER 降级 {len(all_other_nids)} 条 -> {OTHER_FILE}")

    print(f"日志 -> {LOG_FILE}")
    print("完成")

    return total_inserted, total_updated, len(all_other_nids)


if __name__ == "__main__":
    import sys

    paths: list[Path] = []
    if len(sys.argv) > 1:
        paths = [Path(a) for a in sys.argv[1:]]

    ingest(paths if paths else None, init_cloud=False)
