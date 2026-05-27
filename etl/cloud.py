from pathlib import Path
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from sqlmodel import Session, text
from typing import Literal

from database.engine import sqlite_engine, cloud_engine
from database.models import Author, Contest, Tag, Novel, NovelTagLink
from . import logger, log_elapsed

# Global config for bulk insert chunk size
BATCH_SIZE = 1000


class MySQLSyncDataset:
    def __init__(
        self,
        run_mode: Literal["full", "incremental"] = "incremental"
    ):
        """Initialize SQLite to MySQL synchronizer.

        Args:
            run_mode: Sync execution mode.
                - incremental: Default mode for production, perform incremental update.
                - full: Mode for local development only, perform full table refresh.
        """
        self.run_mode: Literal["full", "incremental"] = run_mode
        self.incremental = self.run_mode == "incremental"

        # Store loaded dataframes from SQLite
        self.author_df: pd.DataFrame = pd.DataFrame()
        self.contest_df: pd.DataFrame = pd.DataFrame()
        self.tag_df: pd.DataFrame = pd.DataFrame()
        self.novel_df: pd.DataFrame = pd.DataFrame()
        self.tag_link_df: pd.DataFrame = pd.DataFrame()

    def _clear_all_related_tables(self) -> None:
        """Clear all business tables for full refresh mode."""
        clear_sqls = [
            "SET FOREIGN_KEY_CHECKS = 0;",
            "TRUNCATE TABLE noveltaglink;",
            "TRUNCATE TABLE novel;",
            "TRUNCATE TABLE tag;",
            "TRUNCATE TABLE contest;",
            "TRUNCATE TABLE author;",
            "SET FOREIGN_KEY_CHECKS = 1;"
        ]
        with Session(cloud_engine) as session:
            for sql in clear_sqls:
                session.exec(text(sql))
            session.commit()
        logger.info("All remote tables truncated for full refresh")

    def _batch_write_table(self, df: pd.DataFrame, table_name: str) -> None:
        """Bulk write DataFrame to target MySQL table.

        Convert NaN to None for MySQL NULL compatibility.
        Use INSERT IGNORE to skip duplicate unique keys.

        Args:
            df: Processed DataFrame to be written.
            table_name: Name of target database table.
        """
        if df.empty:
            logger.warning("Table [%s] empty, skip write", table_name)
            return

        # Adapt pandas NaN to MySQL NULL
        df = df.replace({np.nan: None})
        cols = df.columns.tolist()
        col_str = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        insert_sql = f"INSERT IGNORE INTO {table_name} ({col_str}) VALUES ({placeholders})"
        data_tuples = df.to_numpy().tolist()

        with cloud_engine.raw_connection() as conn:
            cursor = conn.cursor()
            try:
                for idx in range(0, len(data_tuples), BATCH_SIZE):
                    batch = data_tuples[idx: idx + BATCH_SIZE]
                    cursor.executemany(insert_sql, batch)
                conn.commit()
                logger.info("Write table [%s] completed", table_name)
            except Exception as e:
                conn.rollback()
                logger.error("Write table [%s] failed, rollback: %s", table_name, str(e))
            finally:
                cursor.close()

    @log_elapsed
    def load_author(self) -> None:
        """Load author data from local SQLite."""
        self.author_df = pd.read_sql(text("SELECT * FROM author"), con=sqlite_engine)

    @log_elapsed
    def load_contest(self) -> None:
        """Load contest data from local SQLite."""
        self.contest_df = pd.read_sql(text("SELECT * FROM contest"), con=sqlite_engine)

    @log_elapsed
    def load_tag(self) -> None:
        """Load tag data from local SQLite."""
        self.tag_df = pd.read_sql(text("SELECT * FROM tag"), con=sqlite_engine)

    @log_elapsed
    def load_novel(self) -> None:
        """Load main novel business data from local SQLite."""
        self.novel_df = pd.read_sql(text("SELECT * FROM novel"), con=sqlite_engine)

    @log_elapsed
    def load_tag_link(self) -> None:
        """Load novel-tag many-to-many relation data from local SQLite."""
        self.tag_link_df = pd.read_sql(text("SELECT * FROM noveltaglink"), con=sqlite_engine)

    @log_elapsed
    def export_dim_tables(self) -> None:
        """Export dimension tables: author, contest, tag."""
        self._batch_write_table(self.author_df, "author")
        self._batch_write_table(self.contest_df, "contest")
        self._batch_write_table(self.tag_df, "tag")

    @log_elapsed
    def export_novel_table(self) -> None:
        """Export main novel table data."""
        self._batch_write_table(self.novel_df, "novel")

    @log_elapsed
    def export_tag_relation(self) -> None:
        """Export novel-tag relation table.

        In incremental mode: delete old relation records first.
        """
        if self.tag_link_df.empty:
            logger.warning("noveltaglink empty, skip write")
            return

        if self.incremental:
            novel_ids = self.tag_link_df["novel_id"].unique().tolist()
            if novel_ids:
                # 修复：SQLModel Session.exec 使用命名参数 params
                placeholders = ", ".join([":n" + str(i) for i in range(len(novel_ids))])
                del_sql = f"DELETE FROM noveltaglink WHERE novel_id IN ({placeholders})"
                params = {f"n{i}": val for i, val in enumerate(novel_ids)}

                with Session(cloud_engine) as session:
                    session.exec(text(del_sql), params=params)
                    session.commit()
                logger.info("Old relation records deleted for incremental sync")

        self._batch_write_table(self.tag_link_df, "noveltaglink")

    @log_elapsed
    def process(self) -> None:
        """Main sync workflow entry.

        Execute full lifecycle: clear(if full) -> load -> export.
        """
        logger.info(f"Start MySQL Sync | Mode: {self.run_mode}")

        # Full mode: truncate all tables first
        if self.run_mode == "full":
            self._clear_all_related_tables()

        # Load all data from local SQLite
        self.load_author()
        self.load_contest()
        self.load_tag()
        self.load_novel()
        self.load_tag_link()

        # Export to remote MySQL in dependency order
        self.export_dim_tables()
        self.export_novel_table()
        self.export_tag_relation()

        logger.info("MySQL sync completed")


if __name__ == "__main__":
    # Temporary log config for local debugging only
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Parse command line argument for running mode
    run_mode: Literal["full", "incremental"] = "incremental"
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("full", "incremental"):
            run_mode = arg

    # Execute sync task
    sync_task = MySQLSyncDataset(run_mode=run_mode)
    sync_task.process()