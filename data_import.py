from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, SQLModel, select

from database import Author, Banner, Contest, Novel, NovelTagLink, Tag
from database import Genre, PType, Status
from database import sqlite_engine
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



def import_dataframe(df: pd.DataFrame, mode: str = "insert") -> tuple[int, int]:
    """将单个清洗后的 DataFrame 写入数据库。

    mode='insert': 假设绝大多数为新数据，新增 bulk insert，少量更新逐行
    mode='update': 假设绝大多数为已有数据，更新 bulk update，少量新增逐行
    返回 (新增数, 更新数, OTHER_nid集合)。
    """
    from sqlalchemy import insert as sa_insert
    from sqlalchemy import update as sa_update
    from sqlalchemy import bindparam

    with Session(sqlite_engine) as session:
        # Phase 1: 批量填充关联表
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

        # Phase 2: 检测已有 nid，区分新增/更新
        all_nids = df["nid"].astype(int).tolist()
        existing_nids: set[int] = set(
            session.exec(select(Novel.id).where(Novel.id.in_(all_nids))).all()
        )

        update_rows: list[dict] = []
        insert_rows: list[dict] = []
        banner_rows: list[dict] = []
        tag_link_rows: list[tuple[int, int]] = []
        tag_link_nids_to_clear: set[int] = set()
        other_nids: set[int] = set()
        now = datetime.now()

        for _, row in df.iterrows():
            nid = int(row["nid"])

            author = author_cache.get(row["author"])
            if author is None:
                continue

            ptype_label = PRICE_TYPE_ID_TO_LABEL.get(int(row["price_type_id"]), "其他")
            ptype = PType.from_label(ptype_label)
            status_label = STATUS_ID_TO_LABEL.get(int(row["status_id"]), "其他")
            status = Status.from_label(status_label)
            genre = Genre.from_label(row["genre"])

            if (ptype == PType.OTHER and ptype_label != "其他") or \
               (status == Status.OTHER and status_label != "其他") or \
               (genre == Genre.OTHER and row["genre"] != "其他"):
                other_nids.add(nid)

            last_update = row["last_update"].to_pydatetime()
            cover = row["cover"] if not pd.isna(row["cover"]) else None
            contest_id = contest_cache.get(row["contest"]).id if not pd.isna(row["contest"]) and row["contest"] in contest_cache else None

            row_dict = {
                "id": nid,
                "title": row["novel_title"],
                "ptype": ptype,
                "genre": genre,
                "status": status,
                "click_num": int(row["click_num"]),
                "word_num": int(row["word_num"]),
                "praise_num": int(row["praise_num"]),
                "like_num": int(row["like_num"]),
                "cover": cover,
                "last_update": last_update,
                "db_update": now,
                "author_id": author.id,
                "contest_id": contest_id,
            }

            if nid in existing_nids:
                update_rows.append(row_dict)
            else:
                insert_rows.append(row_dict)

            # Banner
            banner_url = row["banner"]
            if not pd.isna(banner_url) and banner_url:
                banner_rows.append({"url": banner_url, "novel_id": nid})

            # Tags
            tag_names_list = row["tags"]
            if isinstance(tag_names_list, list) and tag_names_list:
                tag_ids = [
                    tag_cache[name].id
                    for name in dict.fromkeys(tag_names_list)
                    if name in tag_cache
                ]
                if tag_ids:
                    tag_link_nids_to_clear.add(nid)
                    for tid in tag_ids:
                        tag_link_rows.append((tid, nid))

        # Phase 3: 批量写入
        if insert_rows:
            session.execute(sa_insert(Novel.__table__), insert_rows)

        if update_rows:
            if mode == "update":
                # 更新为主：bulk update
                stmt = (
                    sa_update(Novel)
                    .where(Novel.id == bindparam("_id"))
                    .values(
                        title=bindparam("title"),
                        ptype=bindparam("ptype"),
                        genre=bindparam("genre"),
                        status=bindparam("status"),
                        click_num=bindparam("click_num"),
                        word_num=bindparam("word_num"),
                        praise_num=bindparam("praise_num"),
                        like_num=bindparam("like_num"),
                        cover=bindparam("cover"),
                        last_update=bindparam("last_update"),
                        db_update=bindparam("db_update"),
                        author_id=bindparam("author_id"),
                        contest_id=bindparam("contest_id"),
                    )
                )
                for r in update_rows:
                    r["_id"] = r.pop("id")
                with session.bind.connect() as conn:
                    conn.execute(stmt, update_rows)
                    conn.commit()
            else:
                # 插入为主：少数更新逐行
                for row_dict in update_rows:
                    novel = session.get(Novel, row_dict["id"])
                    if novel:
                        for k, v in row_dict.items():
                            if k != "id":
                                setattr(novel, k, v)

        # Banner
        if banner_rows:
            existing_banners = session.exec(
                select(Banner.url, Banner.novel_id)
            ).all()
            existing_banner_set = {(b[0], b[1]) for b in existing_banners}
            new_banners = [
                b for b in banner_rows
                if (b["url"], b["novel_id"]) not in existing_banner_set
            ]
            if new_banners:
                session.execute(sa_insert(Banner.__table__), new_banners)

        # NovelTagLink
        if tag_link_nids_to_clear:
            session.execute(
                NovelTagLink.__table__.delete().where(
                    NovelTagLink.novel_id.in_(tag_link_nids_to_clear)
                )
            )
        if tag_link_rows:
            session.execute(
                sa_insert(NovelTagLink.__table__),
                [{"tag_id": tid, "novel_id": nid} for tid, nid in tag_link_rows],
            )

        session.commit()

    return len(insert_rows), len(update_rows), other_nids


def _process_one(filepath: Path, mode: str = "insert") -> set[int]:
    """处理单个 JSONL 文件并入库，返回 OTHER 降级的 nid 集合。"""
    print(f"处理 {filepath.name} [{mode}] …", end=" ")
    df = load_and_clean(filepath)
    inserted, updated, other_nids = import_dataframe(df, mode)
    print(f"{len(df)} 行 -> 新增 {inserted}, 更新 {updated}")
    return other_nids


if __name__ == "__main__":
    import sys

    SQLModel.metadata.create_all(sqlite_engine)

    mode = "insert"
    paths: list[Path] = []

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--update" in sys.argv:
        mode = "update"
    if "--insert" in sys.argv:
        mode = "insert"

    if args:
        paths = [Path(a) for a in args]
    else:
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
