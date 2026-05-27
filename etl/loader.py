from pathlib import Path
import pandas as pd
from datetime import datetime

from .transform import prep_jsonl
from database.app import create_db_and_table
from database.engine import sqlite_engine


class SQLiteDataset:
    def __init__(self, raw_df: pd.DataFrame):
        self.raw_df = raw_df
        self.tag_col = "tags"
        self.novel_id_col = "nid"
        self.author_col = "author"
        self.contest_col = "contest"

        self.author_df: pd.DataFrame = pd.DataFrame()
        self.contest_df: pd.DataFrame = pd.DataFrame()
        self.tag_df: pd.DataFrame = pd.DataFrame()
        self.tag_exploded_df: pd.DataFrame = pd.DataFrame()
        self.novel_df: pd.DataFrame = pd.DataFrame()
        self.tag_link_df: pd.DataFrame = pd.DataFrame()

    def _write_table(self, df: pd.DataFrame, table_name: str, if_exists: str = "append") -> None:
        if df.empty:
            print(f"Warning: DataFrame for table '{table_name}' is empty, skipping write.")
            return
        print(f"Writing {len(df)} rows to table '{table_name}'...")
        df.to_sql(
            name=table_name,
            con=sqlite_engine,
            if_exists=if_exists,
            index=False,
            chunksize=1000
        )

    def split_author(self) -> None:
        if self.author_col not in self.raw_df.columns:
            return
        df = self.raw_df[[self.author_col]].dropna().drop_duplicates()
        df.rename(columns={self.author_col: "name"}, inplace=True)
        df["id"] = range(1, len(df) + 1)
        # 显式转为可空整型
        df["id"] = df["id"].astype("Int64")
        self.author_df = df

    def split_contest(self) -> None:
        if self.contest_col not in self.raw_df.columns:
            return
        df = self.raw_df[[self.contest_col]].dropna().drop_duplicates()
        df.rename(columns={self.contest_col: "name"}, inplace=True)
        df["id"] = range(1, len(df) + 1)
        # 显式转为可空整型
        df["id"] = df["id"].astype("Int64")
        self.contest_df = df

    def split_tags(self) -> None:
        cols = [self.novel_id_col, self.tag_col]
        if not all(c in self.raw_df.columns for c in cols):
            return
        df_tag_raw = self.raw_df[cols].copy()
        df_exploded = df_tag_raw.explode(self.tag_col)
        df_exploded = df_exploded.dropna(subset=[self.tag_col])
        df_exploded.rename(columns={self.tag_col: "name"}, inplace=True)
        self.tag_exploded_df = df_exploded

        tag_distinct = df_exploded[["name"]].drop_duplicates()
        tag_distinct["id"] = range(1, len(tag_distinct) + 1)
        tag_distinct["id"] = tag_distinct["id"].astype("Int64")
        self.tag_df = tag_distinct

    def split_novel(self) -> None:
        novel_cols = [
            "nid", "title", "ptype", "genre", "status",
            "click_num", "word_num", "praise_num", "like_num",
            "has_banner", "review_num", "comment_num", "cover",
            "last_update", self.author_col, self.contest_col
        ]
        valid_cols = [c for c in novel_cols if c in self.raw_df.columns]
        df = self.raw_df[valid_cols].copy()
        df.rename(columns={"nid": "id"}, inplace=True)
        df["db_update"] = datetime.now()
        self.novel_df = df

    def build_foreign_key(self) -> None:
        # Author foreign key
        if not self.author_df.empty and self.author_col in self.novel_df.columns:
            author_map = dict(zip(self.author_df["name"], self.author_df["id"]))
            self.novel_df["author_id"] = self.novel_df[self.author_col].map(author_map)
            # 强制可空整型
            self.novel_df["author_id"] = self.novel_df["author_id"].astype("Int64")
            self.novel_df.drop(columns=[self.author_col], inplace=True)

        # Contest foreign key (fix type to Int64)
        if not self.contest_df.empty and self.contest_col in self.novel_df.columns:
            contest_map = dict(zip(self.contest_df["name"], self.contest_df["id"]))
            self.novel_df["contest_id"] = self.novel_df[self.contest_col].map(contest_map)
            # 强制可空整型，保证外键为 int
            self.novel_df["contest_id"] = self.novel_df["contest_id"].astype("Int64")
            self.novel_df.drop(columns=[self.contest_col], inplace=True)

    def build_tag_relation(self) -> None:
        if self.tag_exploded_df.empty or self.tag_df.empty:
            return
        tag_map = dict(zip(self.tag_df["name"], self.tag_df["id"]))
        df = self.tag_exploded_df.copy()
        df["tag_id"] = df["name"].map(tag_map)
        df["tag_id"] = df["tag_id"].astype("Int64")
        df.rename(columns={self.novel_id_col: "novel_id"}, inplace=True)
        self.tag_link_df = df[["novel_id", "tag_id"]].dropna()

    def export_all(self) -> None:
        self._write_table(self.author_df[["id", "name"]], "author", if_exists="replace")
        self._write_table(self.contest_df[["id", "name"]], "contest", if_exists="replace")
        self._write_table(self.tag_df[["id", "name"]], "tag", if_exists="replace")
        self._write_table(self.novel_df, "novel", if_exists="replace")
        self._write_table(self.tag_link_df, "noveltaglink", if_exists="replace")

    def process(self) -> None:
        self.split_author()
        self.split_contest()
        self.split_tags()
        self.split_novel()
        self.build_foreign_key()
        self.build_tag_relation()
        self.export_all()


if __name__ == "__main__":
    create_db_and_table(sqlite_engine)

    workplace = Path(__file__).parent.parent
    jsonl_path = workplace / "data.jsonl"
    df_full = prep_jsonl(jsonl_path)

    dataset = SQLiteDataset(df_full)
    dataset.process()

    print("\nAll tables write finished successfully.")