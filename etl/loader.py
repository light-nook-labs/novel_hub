from pathlib import Path
import pandas as pd
from datetime import datetime

from .transform import prep_jsonl
from database.app import create_db_and_table
from database.engine import sqlite_engine


def batch_write_df_to_db(
    df: pd.DataFrame, table_name: str, if_exists: str = "append"
) -> None:
    if df.empty:
        print(
            f"Warning: DataFrame for table '{table_name}' is empty, skipping write."
        )
        return
    print(f"Writing {len(df)} rows to table '{table_name}'...")
    df.to_sql(
        name=table_name,
        con=sqlite_engine,
        if_exists=if_exists,
        index=False,
        chunksize=1000,
    )


if __name__ == "__main__":
    # 重建表结构
    create_db_and_table(sqlite_engine)

    workplace = Path(__file__).parent.parent
    jsonl_path = workplace / "o.jsonl"
    df_full = prep_jsonl(jsonl_path)

    TAG_COL = "tags"
    NOVEL_ID_COL = "nid"
    AUTHOR_COL = "author"
    CONTEST_COL = "contest"

    # 1. 作者表
    if AUTHOR_COL in df_full.columns:
        df_author = df_full[[AUTHOR_COL]].dropna().drop_duplicates()
        df_author.rename(columns={AUTHOR_COL: "name"}, inplace=True)
        batch_write_df_to_db(df_author, "author", if_exists="replace")

    # 2. 赛事表
    if CONTEST_COL in df_full.columns:
        df_contest = df_full[[CONTEST_COL]].dropna().drop_duplicates()
        df_contest.rename(columns={CONTEST_COL: "name"}, inplace=True)
        batch_write_df_to_db(df_contest, "contest", if_exists="replace")

    # 3. 标签处理
    tag_explode = None
    if TAG_COL in df_full.columns and NOVEL_ID_COL in df_full.columns:
        print("\n=== Tags Debug ===")
        df_tag_raw = df_full[[NOVEL_ID_COL, TAG_COL]].copy()
        print(f"原始标签总行数: {len(df_tag_raw)}")

        tag_explode = df_tag_raw.explode(TAG_COL)
        print(f"explode 后总行数: {len(tag_explode)}")

        tag_explode = tag_explode.dropna(subset=[TAG_COL])
        print(f"过滤空标签后行数: {len(tag_explode)}")

        if not tag_explode.empty:
            tag_explode.rename(columns={TAG_COL: "name"}, inplace=True)
            df_tag_distinct = tag_explode[["name"]].drop_duplicates()
            batch_write_df_to_db(df_tag_distinct, "tag", if_exists="replace")

    # 4. 小说主表
    df_full = prep_jsonl(jsonl_path)
    all_df_cols = set(df_full.columns)
    novel_need_cols = [
        "nid",
        "title",
        "ptype",
        "genre",
        "status",
        "click_num",
        "word_num",
        "praise_num",
        "like_num",
        "has_banner",
        "review_num",
        "comment_num",
        "cover",
        "last_update",
        "author_id",
        "contest_id",
    ]
    valid_novel_cols = [c for c in novel_need_cols if c in all_df_cols]
    df_novel = df_full[valid_novel_cols].copy()
    df_novel.rename(columns={"nid": "id"}, inplace=True)
    df_novel["db_update"] = datetime.now()
    batch_write_df_to_db(df_novel, "novel", if_exists="replace")

    # 5. 多对多中间表：使用 SQLite rowid 作为标签ID
    if tag_explode is not None and not tag_explode.empty:
        # SQLite 自增主键用 rowid
        df_tag_db = pd.read_sql(
            "SELECT rowid AS id, name FROM tag", con=sqlite_engine
        )
        tag_map = dict(zip(df_tag_db["name"], df_tag_db["id"]))

        tag_explode["tag_id"] = tag_explode["name"].map(tag_map)
        df_link = tag_explode.rename(columns={NOVEL_ID_COL: "novel_id"})[
            ["novel_id", "tag_id"]
        ].dropna()
        batch_write_df_to_db(df_link, "noveltaglink", if_exists="replace")

    print("\nAll tables write finished successfully.")
