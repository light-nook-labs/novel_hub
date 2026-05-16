from pathlib import Path

import pandas as pd

COVER_BASE = "http://rs.sfacg.com/web/novel/images/NovelCover/Big/"
BANNER_BASE = "http://rs.sfacg.com/web/novel/images/images/"
DEFAULT_COVER = "defaultNew"
COVER_SUFFIX = ".jpg"

PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}


def _compress_banner_url(url) -> str | None:
    """压缩 banner URL，仅保留查询参数。

    beitouNew/{nid}.jpg?2026/5/2 -> 2026/5/2
    前缀和 nid 均可还原，无需存储。
    """
    if not isinstance(url, str):
        return url
    if url.startswith(BANNER_BASE):
        url = url[len(BANNER_BASE) :]
    if "?" in url:
        return url.split("?", 1)[1]
    return url


def load_and_clean(filepath: Path) -> pd.DataFrame:
    """读取单个 JSONL 文件并清洗数据。

    包括去重、缺失值填充、类型转换、非法行过滤。
    """
    df = pd.read_json(filepath, lines=True)

    # 按 nid 去重，保留 last_update 最新的
    df = df.sort_values("last_update").drop_duplicates(
        subset="nid", keep="last"
    )

    # 数值列：缺失填 0 并转 int
    for col in [
        "click_num",
        "word_num",
        "praise_num",
        "like_num",
        "price_type_id",
        "status_id",
    ]:
        df[col] = df[col].fillna(0).astype(int)

    # 时间列：缺失保持 NaT，入库时为 None
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")

    # 字符串列：空串/NaN -> None
    for col in ["cover", "banner", "contest"]:
        df[col] = (
            df[col]
            .replace("", None)
            .where(df[col].notna(), None)
            .astype(object)
        )

    # 去除 CDN 前缀节省存储空间，默认封面直接置空
    df["cover"] = df["cover"].apply(
        lambda u: (
            u[len(COVER_BASE) :]
            if isinstance(u, str) and u.startswith(COVER_BASE)
            else u
        )
    )
    # 默认封面置空，去除冗余后缀
    df["cover"] = df["cover"].apply(
        lambda u: (
            None
            if u == DEFAULT_COVER + COVER_SUFFIX
            else u.removesuffix(COVER_SUFFIX)
            if isinstance(u, str)
            else u
        )
    )
    # banner 仅保留查询参数（其余部分可由 nid + 固定前缀还原）
    df["banner"] = df["banner"].apply(_compress_banner_url)

    # tags：非 list -> []
    df["tags"] = df["tags"].apply(lambda t: t if isinstance(t, list) else [])

    # 过滤 author 为空的行
    df = df.dropna(subset=["author"])
    df = df[df["author"].str.strip() != ""]

    return df
