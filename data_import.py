from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, SQLModel, select

import logging

from db import sqlite_engine
from enums import Genre, PType, Status
from models import Author, Banner, Contest, Novel, NovelTagLink, Tag

# 关闭 db.py 设置的 SQL echo，避免大量日志拖慢导入
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
PROCESSED_DIR = OUTPUT_DIR / "processed"

PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}


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

    # 字符串列：空串/NaN → None，并固定为 object 类型防止 None 被转回 NaN
    for col in ["cover", "banner", "contest"]:
        df[col] = df[col].replace("", None).where(df[col].notna(), None).astype(object)

    # tags：非 list → []
    df["tags"] = df["tags"].apply(lambda t: t if isinstance(t, list) else [])

    # 过滤 author 为空的行
    df = df.dropna(subset=["author"])
    df = df[df["author"].str.strip() != ""]

    return df


def _get_or_create(session, model, name: str, cache: dict):
    """从缓存或 DB 获取记录，不存在则创建。

    缓存以 (model, name) 为 key，避免重复查询。
    """
    key = (model, name)
    if key in cache:
        return cache[key]
    obj = session.exec(select(model).where(model.name == name)).first()
    if obj is None:
        obj = model(name=name)
        session.add(obj)
    cache[key] = obj
    return obj


def import_dataframe(df: pd.DataFrame) -> tuple[int, int]:
    """将单个清洗后的 DataFrame 写入数据库。

    对 Novel 执行 upsert（按 nid），自动处理 Author/Contest/Tag/Banner 关联。
    返回 (新增数, 更新数)。
    """
    inserted, updated = 0, 0
    cache = {}

    with Session(sqlite_engine) as session:
        for _, row in df.iterrows():
            nid = int(row["nid"])

            # Author
            author = _get_or_create(session, Author, row["author"], cache)

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
            if not pd.isna(contest_name) and contest_name:
                novel.contest = _get_or_create(session, Contest, contest_name, cache)
            else:
                novel.contest = None

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

            # Tags (M2M)
            tag_names = row["tags"]
            if isinstance(tag_names, list) and tag_names:
                tag_objs = [
                    _get_or_create(session, Tag, name, cache)
                    for name in dict.fromkeys(tag_names)
                ]
                # 先清除旧关联再设置，避免 UNIQUE 冲突
                if novel.id:
                    for existing in session.exec(
                        select(NovelTagLink).where(NovelTagLink.novel_id == nid)
                    ).all():
                        session.delete(existing)
                    session.flush()
                novel.tags = tag_objs

        session.commit()

    return inserted, updated


def run():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_files = sorted(OUTPUT_DIR.glob("*.jsonl"))

    if not jsonl_files:
        print("无待处理的 .jsonl 文件")
        return

    SQLModel.metadata.create_all(sqlite_engine)

    for filepath in jsonl_files:
        print(f"处理 {filepath.name} …", end=" ")
        df = load_and_clean(filepath)
        inserted, updated = import_dataframe(df)
        # 成功后移走
        filepath.rename(PROCESSED_DIR / filepath.name)
        print(f"{len(df)} 行 → 新增 {inserted}, 更新 {updated} OK")

    print("完成")


if __name__ == "__main__":
    run()
