from pathlib import Path
import pandas as pd
from sqlmodel import Session, select
from pydantic import ValidationError
from tqdm import tqdm

from database.database import create_sqlite_engine, create_db_and_tables, cloud_engine
from database.models import Author, Contest, Novel, Tag, NovelTagLink
from .transform import prep_jsonl
from . import logger, log_elapsed
from database.app import (
    batch_insert_name,
    get_tag_map,
    iter_chunks,
    get_contest_map,
    get_max_author_id,
    drop_all,
)


class RecordFiller:
    def __init__(self, filepath, engine):
        self.filepath = Path(filepath)
        self.engine = engine
        self.df = None

    @log_elapsed
    def load_data(self):
        self.df = prep_jsonl(self.filepath, inplace=True)

    @log_elapsed
    def process_tag(self, chunk_size=1000):
        tag_ser = self.df.explode("tags")["tags"].dropna().drop_duplicates()
        if tag_ser.empty:
            return
        batch_insert_name(self.engine, tag_ser.tolist(), Tag, chunk_size)
        tag_map = get_tag_map(self.engine)
        self.df["tag_id_list"] = self.df["tags"].apply(
            lambda lst: (
                [tag_map[t] for t in lst if t in tag_map]
                if isinstance(lst, list)
                else []
            )
        )

    @log_elapsed
    def process_contest(self, chunk_size=1000):
        contest_ser = self.df["contest"].dropna().drop_duplicates()
        if contest_ser.empty:
            return
        batch_insert_name(self.engine, contest_ser.tolist(), Contest, chunk_size)
        contest_map = get_contest_map(self.engine)
        self.df["contest_id"] = self.df["contest"].map(contest_map)
        # 转为可空整型，避免浮点类型
        self.df["contest_id"] = self.df["contest_id"].astype("Int64")

    @log_elapsed
    def process_author(self, chunk_size=1000):
        df_copy = self.df[["author"]].copy(deep=True)
        df_copy["name_lower"] = df_copy["author"].str.lower()
        df_copy = df_copy.drop_duplicates(subset=["name_lower"], keep="first")
        df_copy.drop(columns=["name_lower"], inplace=True)

        start_id = get_max_author_id(self.engine) or 0
        df_copy["id"] = range(start_id + 1, start_id + 1 + len(df_copy))

        full_data = []
        for _, row in df_copy.iterrows():
            full_data.append({"id": row["id"], "name": row["author"]})

        chunks = list(iter_chunks(full_data, chunk_size))
        with Session(self.engine) as session:
            for chunk in tqdm(chunks, desc="写入作者数据", total=len(chunks)):
                try:
                    for item in chunk:
                        session.add(Author(id=item["id"], name=item["name"]))
                    session.commit()
                except Exception:
                    session.rollback()
                    continue

        # 映射并修正数据类型
        with Session(self.engine) as session:
            name_id_pairs = session.exec(select(Author.name, Author.id)).all()
        name2id = {name: idx for name, idx in name_id_pairs}
        self.df["author"] = self.df["author"].map(name2id)
        self.df.rename(columns={"author": "author_id"}, inplace=True)
        self.df["author_id"] = self.df["author_id"].astype("Int64")

        del df_copy, full_data, chunks, name2id

    @log_elapsed
    def process_novel(self, chunk_size=1000):
        novel_df = self.df.copy()
        novel_df.rename(columns={"nid": "id"}, inplace=True)
        novel_df.drop(
            columns=["tags", "tag_id_list", "contest"], errors="ignore", inplace=True
        )
        novel_df = novel_df.drop_duplicates().dropna(subset=["id"])
        if novel_df.empty:
            return

        idx_chunks = list(iter_chunks(range(len(novel_df)), chunk_size))
        with Session(self.engine) as sess:
            for idx_chunk in tqdm(
                idx_chunks, desc="写入小说数据", total=len(idx_chunks)
            ):
                chunk = novel_df.iloc[idx_chunk]
                records = chunk.to_dict("records")
                # NaN 转为 None 适配 MySQL NULL
                for rec in records:
                    for k, v in rec.items():
                        if pd.isna(v):
                            rec[k] = None
                try:
                    sess.bulk_insert_mappings(Novel, records)
                    sess.commit()
                except (ValidationError, Exception):
                    sess.rollback()
                    continue

        # 清理无用列，仅保留标签关联所需字段
        keep_cols = ["nid", "tag_id_list"]
        drop_cols = [col for col in self.df.columns if col not in keep_cols]
        self.df.drop(columns=drop_cols, errors="ignore", inplace=True)

    @log_elapsed
    def process_tag_link(self, chunk_size=1000):
        link_df = self.df[["nid", "tag_id_list"]].explode("tag_id_list").dropna()
        link_df.rename(
            columns={"nid": "novel_id", "tag_id_list": "tag_id"}, inplace=True
        )
        link_df = link_df[["novel_id", "tag_id"]].drop_duplicates()
        if link_df.empty:
            return

        idx_chunks = list(iter_chunks(range(len(link_df)), chunk_size))
        with Session(self.engine) as sess:
            for idx_chunk in tqdm(
                idx_chunks, desc="处理标签关联", total=len(idx_chunks)
            ):
                chunk = link_df.iloc[idx_chunk]
                records = chunk.to_dict("records")
                try:
                    sess.bulk_insert_mappings(NovelTagLink, records)
                    sess.commit()
                except Exception:
                    sess.rollback()
                    continue

    @log_elapsed
    def run_init(self, chunk_size=1000):
        self.load_data()
        self.process_tag(chunk_size)
        self.process_contest(chunk_size)
        self.process_author(chunk_size)
        self.process_novel(chunk_size)
        self.process_tag_link(chunk_size)
        logger.info("✅ 所有数据处理完毕")


if __name__ == "__main__":
    from database.database import sqlite_engine

    engine = sqlite_engine
    # drop_all(engine, is_keep_tables=False)
    create_db_and_tables(engine)

    filler = RecordFiller("data.jsonl", engine)
    filler.run_init(chunk_size=1000)
