from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from database import Author, Banner, Contest, Novel, NovelTagLink, Tag
from database import Genre, PType, Status
from database import cloud_engine, sqlite_engine
ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"

# 入库时去除 CDN 前缀以节省空间，还原时拼接即可
COVER_BASE = "http://rs.sfacg.com/web/novel/images/NovelCover/Big/"
BANNER_BASE = "http://rs.sfacg.com/web/novel/images/images/"

PRICE_TYPE_ID_TO_LABEL = {0: "免费", 1: "签约", 2: "VIP"}
STATUS_ID_TO_LABEL = {0: "已完结", 1: "连载中", 2: "断更"}

# 云端同步间隔（秒），防止请求过快触发限流
CLOUD_SLEEP = 0.1


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

    # 时间列：缺失保持 NaT，入库时为 None
    df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")

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

    1 次 SELECT + 1 次 bulk INSERT + 1 次 SELECT 替代逐行 add()。
    """
    from sqlalchemy import insert as sa_insert

    existing = session.exec(select(model).where(model.name.in_(names))).all()
    result = {obj.name: obj for obj in existing}
    missing = names - set(result.keys())

    if missing:
        rows = [{"name": n} for n in missing]
        session.execute(sa_insert(model.__table__), rows)
        # 回查新插入的 ID
        new_objs = session.exec(
            select(model).where(model.name.in_(missing))
        ).all()
        for obj in new_objs:
            result[obj.name] = obj

    return result



def _build_row_dict(row, author_id: int, contest_id: int | None, now: datetime) -> dict:
    """将 DataFrame 行转换为 Novel 字典。"""
    ptype_label = PRICE_TYPE_ID_TO_LABEL.get(int(row["price_type_id"]), "其他")
    ptype = PType.from_label(ptype_label)
    status_label = STATUS_ID_TO_LABEL.get(int(row["status_id"]), "其他")
    status = Status.from_label(status_label)
    genre = Genre.from_label(row["genre"])

    cover = row["cover"] if not pd.isna(row["cover"]) else None
    last_update = row["last_update"].to_pydatetime() if not pd.isna(row["last_update"]) else None

    return {
        "id": int(row["nid"]),
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
        "author_id": author_id,
        "contest_id": contest_id,
    }


def _check_other(row, row_dict: dict) -> bool:
    """检查是否有枚举降级为 OTHER，返回 True 表示降级。"""
    ptype = row_dict["ptype"]
    status = row_dict["status"]
    genre = row_dict["genre"]
    ptype_label = PRICE_TYPE_ID_TO_LABEL.get(int(row["price_type_id"]), "其他")
    status_label = STATUS_ID_TO_LABEL.get(int(row["status_id"]), "其他")
    return (
        (ptype == PType.OTHER and ptype_label != "其他")
        or (status == Status.OTHER and status_label != "其他")
        or (genre == Genre.OTHER and row["genre"] != "其他")
    )


def _insert_novels(session, insert_df: pd.DataFrame, caches: dict, now: datetime) -> set[int]:
    """Bulk insert 新数据。返回 OTHER 降级的 nid 集合。

    insert_df 中的 nid 必须全部不在 DB 中。
    """
    from sqlalchemy import insert as sa_insert

    author_cache = caches["authors"]
    contest_cache = caches["contests"]
    tag_cache = caches["tags"]

    rows: list[dict] = []
    banner_rows: list[dict] = []
    tag_link_rows: list[tuple[int, int]] = []
    other_nids: set[int] = set()

    for _, row in insert_df.iterrows():
        nid = int(row["nid"])

        author = author_cache.get(row["author"])
        if author is None:
            continue

        contest_id = (
            contest_cache.get(row["contest"]).id
            if not pd.isna(row["contest"]) and row["contest"] in contest_cache
            else None
        )

        row_dict = _build_row_dict(row, author.id, contest_id, now)
        rows.append(row_dict)

        if _check_other(row, row_dict):
            other_nids.add(nid)

        banner_url = row["banner"]
        if not pd.isna(banner_url) and banner_url:
            banner_rows.append({"url": banner_url, "novel_id": nid})

        tag_names_list = row["tags"]
        if isinstance(tag_names_list, list) and tag_names_list:
            for name in dict.fromkeys(tag_names_list):
                if name in tag_cache:
                    tag_link_rows.append((tag_cache[name].id, nid))

    if rows:
        session.execute(sa_insert(Novel.__table__), rows)

    # Banner
    if banner_rows:
        existing = session.exec(select(Banner.url, Banner.novel_id)).all()
        existing_set = {(b[0], b[1]) for b in existing}
        new_banners = [b for b in banner_rows if (b["url"], b["novel_id"]) not in existing_set]
        if new_banners:
            session.execute(sa_insert(Banner.__table__), new_banners)

    # NovelTagLink
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

    return other_nids


def _update_novels(session, update_df: pd.DataFrame, caches: dict, now: datetime) -> set[int]:
    """Bulk update 已有数据。返回 OTHER 降级的 nid 集合。

    update_df 中的 nid 必须全部已在 DB 中。
    """
    from sqlalchemy import update as sa_update
    from sqlalchemy import bindparam

    author_cache = caches["authors"]
    contest_cache = caches["contests"]
    tag_cache = caches["tags"]

    rows: list[dict] = []
    banner_rows: list[dict] = []
    tag_link_rows: list[tuple[int, int]] = []
    other_nids: set[int] = set()

    for _, row in update_df.iterrows():
        nid = int(row["nid"])

        author = author_cache.get(row["author"])
        if author is None:
            continue

        contest_id = (
            contest_cache.get(row["contest"]).id
            if not pd.isna(row["contest"]) and row["contest"] in contest_cache
            else None
        )

        row_dict = _build_row_dict(row, author.id, contest_id, now)
        rows.append(row_dict)

        if _check_other(row, row_dict):
            other_nids.add(nid)

        banner_url = row["banner"]
        if not pd.isna(banner_url) and banner_url:
            banner_rows.append({"url": banner_url, "novel_id": nid})

        tag_names_list = row["tags"]
        if isinstance(tag_names_list, list) and tag_names_list:
            for name in dict.fromkeys(tag_names_list):
                if name in tag_cache:
                    tag_link_rows.append((tag_cache[name].id, nid))

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

    # Banner
    if banner_rows:
        existing = session.exec(select(Banner.url, Banner.novel_id)).all()
        existing_set = {(b[0], b[1]) for b in existing}
        new_banners = [b for b in banner_rows if (b["url"], b["novel_id"]) not in existing_set]
        if new_banners:
            from sqlalchemy import insert as sa_insert
            session.execute(sa_insert(Banner.__table__), new_banners)

    # NovelTagLink
    if tag_link_rows:
        nids_to_clear = {nid for _, nid in tag_link_rows}
        if nids_to_clear:
            session.execute(
                NovelTagLink.__table__.delete().where(
                    NovelTagLink.novel_id.in_(nids_to_clear)
                )
            )
        from sqlalchemy import insert as sa_insert
        session.execute(
            sa_insert(NovelTagLink.__table__),
            [{"tag_id": tid, "novel_id": nid} for tid, nid in tag_link_rows],
        )

    return other_nids


def commit_dataframe(df: pd.DataFrame, engine=sqlite_engine) -> tuple[int, int]:
    """将单个清洗后的 DataFrame 写入数据库（事务原子性）。

    自动检测 nid 区分新增/更新，分别调用 _insert_novels / _update_novels。
    单次调用内全部操作在同一事务中，失败自动回滚。
    engine 默认为 sqlite_engine，也可传入 cloud_engine 同步到云端。
    返回 (新增数, 更新数, OTHER_nid集合)。
    """
    with Session(engine) as session:
        try:
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

            caches = {"authors": author_cache, "contests": contest_cache, "tags": tag_cache}
            now = datetime.now()

            # Phase 2: 按 nid 拆分为新增/更新
            all_nids = df["nid"].astype(int).tolist()
            existing_nids: set[int] = set(
                session.exec(select(Novel.id).where(Novel.id.in_(all_nids))).all()
            )

            mask_existing = df["nid"].astype(int).isin(existing_nids)
            df_new = df[~mask_existing]
            df_old = df[mask_existing]

            # Phase 3: 分别处理
            other_new = _insert_novels(session, df_new, caches, now) if len(df_new) > 0 else set()
            other_old = _update_novels(session, df_old, caches, now) if len(df_old) > 0 else set()

            session.commit()
        except Exception:
            session.rollback()
            raise

    return len(df_new), len(df_old), other_new | other_old


def _sync_to_cloud(df: pd.DataFrame) -> tuple[int, int]:
    """同步数据到 PostgreSQL，含重试机制。

    云端数据库未配置时跳过；连接不稳定时最多重试 3 次，指数退避。
    返回 (新增数, 更新数)。
    """
    import time

    if cloud_engine is None:
        return 0, 0

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            inserted, updated, _ = commit_dataframe(df, cloud_engine)
            time.sleep(CLOUD_SLEEP)
            return inserted, updated
        except Exception as e:
            if attempt < retries:
                delay = 2 ** attempt
                print(f"[cloud retry {attempt}/{retries} in {delay}s]", end=" ", flush=True)
                time.sleep(delay)
            else:
                print(f"[cloud FAILED after {retries} attempts: {e}]")
                raise


def _process_one(filepath: Path) -> dict:
    """处理单个 JSONL 文件并写入本地 SQLite，返回统计信息和 DataFrame。

    本地库写入为原子事务，确保数据一致性。
    """
    import time

    print(f"{filepath.name} …", end=" ", flush=True)
    t_load0 = time.perf_counter()
    df = load_and_clean(filepath)
    t_load = time.perf_counter() - t_load0

    t_sqlite0 = time.perf_counter()
    inserted, updated, other_nids = commit_dataframe(df)
    t_sqlite = time.perf_counter() - t_sqlite0

    total = t_load + t_sqlite
    print(f"{len(df)} 行 | +{inserted} ~{updated} | {total:.1f}s")
    return {
        "file": filepath.name,
        "rows": len(df),
        "inserted": inserted,
        "updated": updated,
        "other": len(other_nids),
        "other_nids": other_nids,
        "t_sqlite": t_sqlite,
        "total": total,
        "df": df,
    }


if __name__ == "__main__":
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor

    from database.app import create_db_and_table

    create_db_and_table(sqlite_engine)

    paths: list[Path] = []
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
    all_other_nids: set[int] = set()
    total_inserted, total_updated = 0, 0

    for filepath, df in zip(paths, dfs):
        t_write0 = time.perf_counter()
        inserted, updated, other_nids = commit_dataframe(df)
        t_write = time.perf_counter() - t_write0

        total_inserted += inserted
        total_updated += updated
        all_other_nids.update(other_nids)
        print(f"  {filepath.name}: {len(df)} 行 | +{inserted} ~{updated} | {t_write:.1f}s")
        log_lines.append(
            f"{datetime.now():%Y-%m-%d %H:%M:%S} | {filepath.name} | SQLite | "
            f"rows={len(df)} ins={inserted} upd={updated} "
            f"other={len(other_nids)} | {t_write:.1f}s"
        )

    # Phase 3: 一次性同步云端
    if cloud_engine is not None:
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
