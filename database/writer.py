from datetime import datetime

import pandas as pd
from sqlalchemy import bindparam
from sqlalchemy import insert as sa_insert
from sqlalchemy import update as sa_update
from sqlmodel import Session, select

from database.cleaner import PRICE_TYPE_ID_TO_LABEL, STATUS_ID_TO_LABEL
from database.enums import Genre, PType, Status
from database.models import Author, Banner, Contest, Novel, NovelTagLink, Tag

_BATCH_UPSERT_CHUNK = 200


def _batch_upsert(session, model, names: set[str]) -> dict[str, object]:
    """批量查找或创建 name 型记录，返回 {name: obj} 映射。

    1 次 SELECT + N 次小批量 bulk INSERT + 1 次 SELECT 替代逐行 add()。
    云端 PostgreSQL 有 statement_timeout，单次 INSERT 不宜过大。
    """
    existing = session.exec(select(model).where(model.name.in_(names))).all()
    result = {obj.name: obj for obj in existing}
    missing = list(names - set(result.keys()))

    for i in range(0, len(missing), _BATCH_UPSERT_CHUNK):
        chunk_names = missing[i : i + _BATCH_UPSERT_CHUNK]
        rows = [{"name": n} for n in chunk_names]
        session.execute(sa_insert(model.__table__), rows)

    if missing:
        new_objs = session.exec(
            select(model).where(model.name.in_(missing))
        ).all()
        for obj in new_objs:
            result[obj.name] = obj

    return result


def _build_row_dict(
    row, author_id: int, contest_id: int | None, now: datetime
) -> dict:
    """将 DataFrame 行转换为 Novel 字典。"""
    ptype_label = PRICE_TYPE_ID_TO_LABEL.get(int(row.price_type_id), "其他")
    ptype = PType.from_label(ptype_label)
    status_label = STATUS_ID_TO_LABEL.get(int(row.status_id), "其他")
    status = Status.from_label(status_label)
    genre = Genre.from_label(row.genre)

    cover = row.cover if not pd.isna(row.cover) else None
    last_update = (
        row.last_update.to_pydatetime()
        if not pd.isna(row.last_update)
        else None
    )

    return {
        "id": int(row.nid),
        "title": row.novel_title,
        "ptype": ptype,
        "genre": genre,
        "status": status,
        "click_num": int(row.click_num),
        "word_num": int(row.word_num),
        "praise_num": int(row.praise_num),
        "like_num": int(row.like_num),
        "cover": cover,
        "last_update": last_update,
        "db_update": now,
        "author_id": author_id,
        "contest_id": contest_id,
    }


def _check_other(row, row_dict: dict) -> bool:
    """检查是否有枚举降级为 OTHER，返回 True 表示降级。"""
    ptype = row_dict["ptype"]
    status = row_dict["status"]
    genre = row_dict["genre"]
    ptype_label = PRICE_TYPE_ID_TO_LABEL.get(int(row.price_type_id), "其他")
    status_label = STATUS_ID_TO_LABEL.get(int(row.status_id), "其他")
    return (
        (ptype == PType.OTHER and ptype_label != "其他")
        or (status == Status.OTHER and status_label != "其他")
        or (genre == Genre.OTHER and row.genre != "其他")
    )


def _collect_rows(
    df: pd.DataFrame, caches: dict, now: datetime
) -> tuple[list[dict], list[dict], list[tuple[int, int]], set[int]]:
    """遍历 DataFrame 收集 Novel 行、Banner、TagLink 和 OTHER nid。

    抽取 _insert_novels / _update_novels 中重复的迭代逻辑。
    """
    author_cache = caches["authors"]
    contest_cache = caches["contests"]
    tag_cache = caches["tags"]

    rows: list[dict] = []
    banner_rows: list[dict] = []
    tag_link_rows: list[tuple[int, int]] = []
    other_nids: set[int] = set()

    for row in df.itertuples():
        nid = int(row.nid)

        author = author_cache.get(row.author)
        if author is None:
            continue

        contest_id = (
            contest_cache.get(row.contest).id
            if not pd.isna(row.contest) and row.contest in contest_cache
            else None
        )

        row_dict = _build_row_dict(row, author.id, contest_id, now)
        rows.append(row_dict)

        if _check_other(row, row_dict):
            other_nids.add(nid)

        banner_url = row.banner
        if not pd.isna(banner_url) and banner_url:
            banner_rows.append({"url": banner_url, "novel_id": nid})

        tag_names_list = row.tags
        if isinstance(tag_names_list, list) and tag_names_list:
            for name in dict.fromkeys(tag_names_list):
                if name in tag_cache:
                    tag_link_rows.append((tag_cache[name].id, nid))

    return rows, banner_rows, tag_link_rows, other_nids


def _write_banners_and_tags(
    session, banner_rows: list[dict], tag_link_rows: list[tuple[int, int]]
) -> None:
    """写入 Banner（去重插入）和 NovelTagLink（删旧插新）。"""
    if banner_rows:
        urls = [b["url"] for b in banner_rows]
        existing = session.exec(
            select(Banner.url, Banner.novel_id).where(Banner.url.in_(urls))
        ).all()
        existing_set = {(b[0], b[1]) for b in existing}
        new_banners = [
            b
            for b in banner_rows
            if (b["url"], b["novel_id"]) not in existing_set
        ]
        if new_banners:
            session.execute(sa_insert(Banner.__table__), new_banners)

    if tag_link_rows:
        nids_to_clear = {nid for _, nid in tag_link_rows}
        if nids_to_clear:
            session.execute(
                NovelTagLink.__table__.delete().where(
                    NovelTagLink.novel_id.in_(nids_to_clear)
                )
            )
        session.execute(
            sa_insert(NovelTagLink.__table__),
            [{"tag_id": tid, "novel_id": nid} for tid, nid in tag_link_rows],
        )


def _insert_novels(
    session, insert_df: pd.DataFrame, caches: dict, now: datetime
) -> set[int]:
    """Bulk insert 新数据。返回 OTHER 降级的 nid 集合。

    insert_df 中的 nid 必须全部不在 DB 中。
    """
    rows, banner_rows, tag_link_rows, other_nids = _collect_rows(
        insert_df, caches, now
    )

    if rows:
        session.execute(sa_insert(Novel.__table__), rows)

    _write_banners_and_tags(session, banner_rows, tag_link_rows)
    return other_nids


def _update_novels(
    session, update_df: pd.DataFrame, caches: dict, now: datetime
) -> set[int]:
    """Bulk update 已有数据。返回 OTHER 降级的 nid 集合。

    update_df 中的 nid 必须全部已在 DB 中。
    """
    rows, banner_rows, tag_link_rows, other_nids = _collect_rows(
        update_df, caches, now
    )

    if rows:
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
        for r in rows:
            r["_id"] = r.pop("id")
        session.connection().execute(stmt, rows)

    _write_banners_and_tags(session, banner_rows, tag_link_rows)
    return other_nids


def commit_dataframe(
    df: pd.DataFrame, engine=None, known_nids: set[int] | None = None
) -> tuple[int, int, set[int]]:
    """将单个清洗后的 DataFrame 写入数据库（事务原子性）。

    自动检测 nid 区分新增/更新。known_nids 用于跨文件缓存，减少 DB 查询。
    返回 (新增数, 更新数, OTHER_nid集合)。
    """
    if engine is None:
        from database.engine import sqlite_engine

        engine = sqlite_engine

    with Session(engine) as session:
        try:
            # Phase 1: 批量填充关联表
            author_names = set(df["author"].dropna().str.strip())
            author_names.discard("")
            author_cache = _batch_upsert(session, Author, author_names)

            contest_names = set(
                df["contest"]
                .dropna()
                .apply(lambda x: x if x != "" else None)
                .dropna()
            )
            contest_cache = _batch_upsert(session, Contest, contest_names)

            tag_names: set[str] = set()
            for tags in df["tags"].dropna():
                if isinstance(tags, list):
                    tag_names.update(tags)
            tag_cache = _batch_upsert(session, Tag, tag_names)

            session.flush()

            caches = {
                "authors": author_cache,
                "contests": contest_cache,
                "tags": tag_cache,
            }
            now = datetime.now()

            # Phase 2: 按 nid 拆分为新增/更新
            all_nids = df["nid"].astype(int).tolist()
            all_nids_set = set(all_nids)

            if known_nids is not None:
                existing_nids = all_nids_set & known_nids
                unknown = all_nids_set - known_nids
                if unknown:
                    db_existing = set(
                        session.exec(
                            select(Novel.id).where(Novel.id.in_(unknown))
                        ).all()
                    )
                    existing_nids |= db_existing
                    known_nids.update(all_nids_set)
            else:
                existing_nids = set(
                    session.exec(
                        select(Novel.id).where(Novel.id.in_(all_nids))
                    ).all()
                )

            mask_existing = df["nid"].astype(int).isin(existing_nids)
            df_new = df[~mask_existing]
            df_old = df[mask_existing]

            # Phase 3: 分别处理
            other_new = (
                _insert_novels(session, df_new, caches, now)
                if len(df_new) > 0
                else set()
            )
            other_old = (
                _update_novels(session, df_old, caches, now)
                if len(df_old) > 0
                else set()
            )

            session.commit()
        except Exception:
            session.rollback()
            raise

    return len(df_new), len(df_old), other_new | other_old
