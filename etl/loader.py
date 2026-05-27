from pathlib import Path
import sys
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from typing import Literal

from database.app import create_db_and_table
from database.engine import sqlite_engine
from .transform import prep_jsonl
from . import logger, log_elapsed


class SQLiteDataset:
    def __init__(
        self,
        raw_df: pd.DataFrame,
        run_mode: Literal["full", "incremental"] = "incremental"
    ):
        """Initialize SQLite ETL handler.

        Args:
            raw_df: Source raw DataFrame containing original business data.
            run_mode: ETL execution mode.
                - incremental: Default mode for production, perform incremental update.
                - full: Mode for local development only, perform full table refresh.
        """
        self.raw_df = raw_df
        self.run_mode: Literal["full", "incremental"] = run_mode
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

    def _write_table(self, df: pd.DataFrame, table_name: str) -> None:
        """Write DataFrame data to target SQLite table.

        Args:
            df: Processed DataFrame to be written.
            table_name: Name of target database table.
        """
        if df.empty:
            logger.warning("Table [%s] empty, skip write", table_name)
            return

        if self.run_mode == "full":
            df.to_sql(
                name=table_name,
                con=sqlite_engine,
                if_exists="append",
                index=False,
                chunksize=1000
            )
        else:
            # Insert and ignore duplicate unique keys for incremental mode
            cols = df.columns.tolist()
            col_str = ", ".join(cols)
            placeholders = ", ".join(["?"] * len(cols))
            insert_sql = f"INSERT OR IGNORE INTO {table_name} ({col_str}) VALUES ({placeholders})"
            with sqlite_engine.connect() as conn:
                conn.executemany(insert_sql, df.to_numpy().tolist())
                conn.commit()

    def _clear_all_related_tables(self) -> None:
        """Clear data of dimension tables and relation table for full refresh."""
        clear_sqls = [
            "DELETE FROM noveltaglink;",
            "DELETE FROM tag;",
            "DELETE FROM contest;",
            "DELETE FROM author;"
        ]
        with sqlite_engine.connect() as conn:
            for sql in clear_sqls:
                conn.execute(text(sql))
            conn.commit()

    @log_elapsed
    def split_author(self) -> None:
        """Extract distinct author data from source DataFrame."""
        if self.author_col not in self.raw_df.columns:
            return
        df = self.raw_df[[self.author_col]].dropna().drop_duplicates(keep="first")
        df.rename(columns={self.author_col: "name"}, inplace=True)
        self.author_df = df

    @log_elapsed
    def split_contest(self) -> None:
        """Extract distinct contest data from source DataFrame."""
        if self.contest_col not in self.raw_df.columns:
            return
        df = self.raw_df[[self.contest_col]].dropna().drop_duplicates(keep="first")
        df.rename(columns={self.contest_col: "name"}, inplace=True)
        self.contest_df = df

    @log_elapsed
    def split_tags(self) -> None:
        """Split tag column and extract distinct tag data.

        Explode list-type tag field and deduplicate tag names.
        """
        cols = [self.novel_id_col, self.tag_col]
        if not all(c in self.raw_df.columns for c in cols):
            return
        df_tag_raw = self.raw_df[cols].copy()
        df_exploded = df_tag_raw.explode(self.tag_col).dropna(subset=[self.tag_col])
        df_exploded.rename(columns={self.tag_col: "name"}, inplace=True)
        self.tag_exploded_df = df_exploded
        tag_distinct = df_exploded[["name"]].drop_duplicates(keep="first")
        self.tag_df = tag_distinct

    @log_elapsed
    def split_novel(self) -> None:
        """Extract main novel business data from source DataFrame."""
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

    @log_elapsed
    def build_foreign_key(self) -> None:
        """Map dimension table primary key to novel table foreign key."""
        if not self.author_df.empty and self.author_col in self.novel_df.columns:
            self._write_table(self.author_df, "author")
            author_db_df = pd.read_sql("SELECT id, name FROM author", con=sqlite_engine)
            author_map = author_db_df.set_index("name")["id"]
            self.novel_df["author_id"] = self.novel_df[self.author_col].map(author_map)
            self.novel_df["author_id"] = self.novel_df["author_id"].astype("Int64")
            self.novel_df.drop(columns=[self.author_col], inplace=True)

        if not self.contest_df.empty and self.contest_col in self.novel_df.columns:
            self._write_table(self.contest_df, "contest")
            contest_db_df = pd.read_sql("SELECT id, name FROM contest", con=sqlite_engine)
            contest_map = contest_db_df.set_index("name")["id"]
            self.novel_df["contest_id"] = self.novel_df[self.contest_col].map(contest_map)
            self.novel_df["contest_id"] = self.novel_df["contest_id"].astype("Int64")
            self.novel_df.drop(columns=[self.contest_col], inplace=True)

    @log_elapsed
    def build_tag_relation(self) -> None:
        """Build many-to-many relation between novel and tag tables."""
        if self.tag_exploded_df.empty or self.tag_df.empty:
            return
        self._write_table(self.tag_df, "tag")
        tag_db_df = pd.read_sql("SELECT id, name FROM tag", con=sqlite_engine)
        tag_map = tag_db_df.set_index("name")["id"]
        df = self.tag_exploded_df.copy()
        df["tag_id"] = df["name"].map(tag_map)
        df["tag_id"] = df["tag_id"].astype("Int64")
        df.rename(columns={self.novel_id_col: "novel_id"}, inplace=True)
        df = df[["novel_id", "tag_id"]].dropna().drop_duplicates(keep="first")
        self.tag_link_df = df

    @log_elapsed
    def export_all(self) -> None:
        """Export all processed data to corresponding database tables.

        Overwrite novel table directly, handle tag relation table by running mode.
        """
        # Overwrite novel table with latest data
        self.novel_df.to_sql(
            name="novel",
            con=sqlite_engine,
            if_exists="replace",
            index=False,
            chunksize=1000
        )

        if self.run_mode == "full":
            self._write_table(self.tag_link_df, "noveltaglink")
        else:
            # Remove old relations before inserting new ones in incremental mode
            novel_ids = self.novel_df["id"].tolist()
            if novel_ids:
                placeholders = ", ".join(["?"] * len(novel_ids))
                del_sql = f"DELETE FROM noveltaglink WHERE novel_id IN ({placeholders})"
                with sqlite_engine.connect() as conn:
                    conn.execute(text(del_sql), novel_ids)
                    conn.commit()
            self._write_table(self.tag_link_df, "noveltaglink")

    @log_elapsed
    def process(self) -> None:
        """Main ETL workflow entry.

        Execute full lifecycle: prepare -> transform -> load.
        """
        logger.info(f"Start ETL | Mode: {self.run_mode}")
        if self.run_mode == "full":
            self._clear_all_related_tables()

        self.split_author()
        self.split_contest()
        self.split_tags()
        self.split_novel()
        self.build_foreign_key()
        self.build_tag_relation()
        self.export_all()
        logger.info("ETL completed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Parse command line argument for running mode
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("full", "incremental"):
            run_mode = arg  # type: ignore

    # Initialize database tables
    create_db_and_table(sqlite_engine)

    # Load source data
    workplace = Path(__file__).parent.parent
    jsonl_path = workplace / "data.jsonl"
    df_full = prep_jsonl(jsonl_path)
    logger.info(f"Load source data | Total rows: {len(df_full)}")

    # Execute ETL task
    dataset = SQLiteDataset(df_full, run_mode='full')
    dataset.process()