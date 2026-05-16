import time

import pandas as pd

from database.engine import cloud_engine
from database.writer import commit_dataframe

CLOUD_CHUNK_SIZE = 10000
CLOUD_SLEEP = 0.1


def _sync_to_cloud(df: pd.DataFrame) -> tuple[int, int]:
    """分块同步到云端，每块独立事务，含重试机制。

    云端未配置时跳过；连接不稳定时最多重试 3 次，指数退避。
    返回 (新增数, 更新数)。
    """
    if cloud_engine is None:
        return 0, 0

    total_ins, total_upd = 0, 0
    chunks = range(0, len(df), CLOUD_CHUNK_SIZE)

    for i, start in enumerate(chunks):
        chunk = df.iloc[start : start + CLOUD_CHUNK_SIZE]

        retries = 3
        for attempt in range(1, retries + 1):
            try:
                ins, upd, _ = commit_dataframe(chunk, cloud_engine)
                total_ins += ins
                total_upd += upd
                break
            except Exception as e:
                if attempt < retries:
                    delay = 2**attempt
                    print(
                        f"[cloud chunk {i} retry {attempt}/{retries} in {delay}s]",
                        end=" ",
                        flush=True,
                    )
                    time.sleep(delay)
                else:
                    print(f"[cloud chunk {i} FAILED: {e}]")
                    raise

        time.sleep(CLOUD_SLEEP)

    return total_ins, total_upd
