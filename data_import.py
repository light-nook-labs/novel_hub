import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, SQLModel, select

from db import sqlite_engine
from enums import Genre, PType, Status
from models import Author, Banner, Contest, Novel, NovelTagLink, Tag

# 关闭 db.py 设置的 SQL echo，避免大量日志拖慢导入
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"

# 入库时去除 CDN 前缀以节省空间，还原时拼接即可
COVER_BASE = "http://rs.sfacg.com/web/novel/images/NovelCover/Big/"
BANNER_BASE = "http://rs.sfacg.com/web/novel/images/images/"

PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}


def _compress_banner_url(url) -> str | None:
    """压缩 banner URL，仅保留查询参数。

    beitouNew/{nid}.jpg?2026/5/2 → 2026/5/2
    前缀和 nid 均可还原，无需存储。
    """
    if not isinstance(url, str):
        return url
    if url.startswith(BANNER_BASE):
        url = url[len(BANNER_BASE):]
    if "?" in url:
        return url.split("?", 1)[1]
    return url


def load_and_clean(filepath: Path) -> pd.DataFrame:
    """读取单个 JSONL 文件并清洗数据。

    包括去重、缺失值填充、类型转换、非法行过滤。
    """
    df = pd.read_json(filepath, lines=True)

    # 按 nid 去重，保留 last_update 最新的
    df = df.sort_values("last_update").drop_duplicates(subset="nid", keep="last")

    # 数值列：缺失填 0 并转 int
    for col in ["click_num", "word_num", "praise_num", "like_num",
                "price_type_id", "status_id"]:
        df[col] = df[col].fillna(0).astype(int)

    # 时间列
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")
    df["last_update"] = df["last_update"].fillna(datetime.now())

    # 字符串列：空串/NaN → None
    for col in ["cover", "banner", "contest"]:
        df[col] = df[col].replace("", None).where(df[col].notna(), None).astype(object)

    # 去除 CDN 前缀节省存储空间
    df["cover"] = df["cover"].apply(
        lambda u: u[len(COVER_BASE):] if isinstance(u, str) and u.startswith(COVER_BASE) else u
    )
    # banner 仅保留查询参数（其余部分可由 nid + 固定前缀还原）
    df["banner"] = df["banner"].apply(_compress_banner_url)

    # tags：非 list → []
    df["tags"] = df["tags"].apply(lambda t: t if isinstance(t, list) else [])

    # 过滤 author 为空的行
    df = df.dropna(subset=["author"])
    df = df[df["author"].str.strip() != ""]

    return df


def _batch_upsert(session, model, names: set[str]) -> dict[str, object]:
    """批量查找或创建 name 型记录，返回 {name: obj} 映射。

    先查询 DB 中已存在的，再批量插入缺失的，避免逐行 SELECT。
    """
    existing = session.exec(select(model).where(model.name.in_(names))).all()
    result = {obj.name: obj for obj in existing}
    missing = names - set(result.keys())
    for name in missing:
        obj = model(name=name)
        session.add(obj)
        result[name] = obj
    return result



def import_dataframe(df: pd.DataFrame) -> tuple[int, int]:
    """将单个清洗后的 DataFrame 写入数据库。

    两阶段：先批量填充 Contest/Tag/Author 等小表，再逐行写入 Novel。
    返回 (新增数, 更新数)。
    """
    with Session(sqlite_engine) as session:
        # ── Phase 1: 批量填充关联表 ──────────────────────────────────
        author_names = set(df["author"].dropna().str.strip())
        author_names.discard("")
        author_cache = _batch_upsert(session, Author, author_names)

        contest_names = set(
            df["contest"].dropna().apply(lambda x: x if x != "" else None).dropna()
        )
        contest_cache = _batch_upsert(session, Contest, contest_names)

        tag_names: set[str] = set()
        for tags in df["tags"].dropna():
            if isinstance(tags, list):
                tag_names.update(tags)
        tag_cache = _batch_upsert(session, Tag, tag_names)

        session.flush()

        # ── Phase 2: 逐行写入 Novel ──────────────────────────────────
        inserted, updated = 0, 0

        for _, row in df.iterrows():
            nid = int(row["nid"])

            # Author
            author = author_cache.get(row["author"])
            if author is None:
                continue

            # 枚举映射：ID → label → enum
            ptype = PType.from_label(
                PRICE_TYPE_ID_TO_LABEL.get(int(row["price_type_id"]), "其他")
            )
            status = Status.from_label(
                STATUS_ID_TO_LABEL.get(int(row["status_id"]), "其他")
            )
            genre = Genre.from_label(row["genre"])

            # Novel (upsert by nid)
            novel = session.get(Novel, nid)
            if novel is None:
                novel = Novel(id=nid)
                session.add(novel)
                inserted += 1
            else:
                updated += 1

            novel.title = row["novel_title"]
            novel.ptype = ptype
            novel.genre = genre
            novel.status = status
            novel.click_num = int(row["click_num"])
            novel.word_num = int(row["word_num"])
            novel.praise_num = int(row["praise_num"])
            novel.like_num = int(row["like_num"])
            novel.cover = row["cover"] if not pd.isna(row["cover"]) else None
            novel.last_update = row["last_update"].to_pydatetime()
            novel.author = author

            # Contest
            contest_name = row["contest"]
            novel.contest = contest_cache.get(contest_name) if not pd.isna(contest_name) else None

            # Banner
            banner_url = row["banner"]
            if not pd.isna(banner_url) and banner_url:
                existing = session.exec(
                    select(Banner).where(
                        Banner.url == banner_url, Banner.novel_id == nid
                    )
                ).first()
                if not existing:
                    session.add(Banner(url=banner_url, novel=novel))

            # Tags (M2M) — 只做关联，tag 已在 Phase 1 创建
            tag_names_list = row["tags"]
            if isinstance(tag_names_list, list) and tag_names_list:
                tag_objs = [
                    tag_cache[name]
                    for name in dict.fromkeys(tag_names_list)
                    if name in tag_cache
                ]
                if tag_objs:
                    for link in session.exec(
                        select(NovelTagLink).where(NovelTagLink.novel_id == nid)
                    ).all():
                        session.delete(link)
                    session.flush()
                    novel.tags = tag_objs

        session.commit()

    return inserted, updated


def _process_one(filepath: Path):
    """处理单个 JSONL 文件并入库。"""
    print(f"处理 {filepath.name} …", end=" ")
    df = load_and_clean(filepath)
    inserted, updated = import_dataframe(df)
    print(f"{len(df)} 行 -> 新增 {inserted}, 更新 {updated}")


if __name__ == "__main__":
    import sys

    SQLModel.metadata.create_all(sqlite_engine)

    if len(sys.argv) > 1:
        # uv run data_import.py path/to/file.jsonl
        _process_one(Path(sys.argv[1]))
    else:
        # uv run data_import.py — 遍历 output/ 下所有 jsonl
        jsonl_files = sorted(OUTPUT_DIR.glob("*.jsonl"))
        if not jsonl_files:
            print("无待处理的 .jsonl 文件")
        else:
            for filepath in jsonl_files:
                _process_one(filepath)

    print("完成")
