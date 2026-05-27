import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from sqlmodel import Session, text
from typing import Literal
from tqdm import tqdm

from database.engine import sqlite_engine, cloud_engine
from . import logger, log_elapsed

# 全局配置
SMALL_TABLE_THRESHOLD = 500
BIG_TABLE_BATCH = 1000
COMMIT_INTERVAL = 5

# 标记每张表中需要转为布尔类型的字段
TABLE_BOOL_COLS = {
    "tag": [],
    "contest": [],
    "author": [],
    "novel": ["has_banner"],
    "noveltaglink": [],
}


class BaseSyncDataset(ABC):
    """数据同步抽象基类，抽取所有公共逻辑"""

    def __init__(self, run_mode: Literal["full", "incremental"] = "incremental"):
        self.run_mode = run_mode
        self.incremental = self.run_mode == "incremental"

        # 数据表容器
        self.author_df = pd.DataFrame()
        self.contest_df = pd.DataFrame()
        self.tag_df = pd.DataFrame()
        self.novel_df = pd.DataFrame()
        self.tag_link_df = pd.DataFrame()

    @abstractmethod
    def _clear_all_related_tables(self) -> None:
        """清空表数据，由子类实现差异化 SQL"""
        pass

    @abstractmethod
    def _build_insert_sql(
        self, table_name: str, cols: list, batch: list
    ) -> tuple[str, list]:
        """
        构造 INSERT SQL + 参数列表
        由 MySQL / Postgres 子类分别实现占位符、冲突处理、类型转换
        """
        pass

    def _batch_write_table(self, df: pd.DataFrame, table_name: str) -> None:
        """通用批量写入逻辑"""
        if df.empty:
            logger.warning(f"Table [{table_name}] empty, skip write")
            return

        df = df.replace({np.nan: None})
        cols = df.columns.tolist()
        data_list = df.to_numpy().tolist()
        total_rows = len(data_list)
        logger.info(f"Table [{table_name}] total rows to write: {total_rows}")

        with cloud_engine.raw_connection() as conn:
            cursor = conn.cursor()
            try:
                if total_rows < SMALL_TABLE_THRESHOLD:
                    sql, params = self._build_insert_sql(table_name, cols, data_list)
                    cursor.execute(sql, params)
                    conn.commit()
                    logger.info(
                        f"[{table_name}] Small table done, inserted: {total_rows}"
                    )
                else:
                    batch_idx = 0
                    total_batch = (total_rows + BIG_TABLE_BATCH - 1) // BIG_TABLE_BATCH

                    with tqdm(
                        total=total_batch,
                        desc=f"{self._db_prefix} {table_name}",
                        unit="batch",
                        leave=True,
                    ) as pbar:
                        for idx in range(0, total_rows, BIG_TABLE_BATCH):
                            batch = data_list[idx : idx + BIG_TABLE_BATCH]
                            batch_idx += 1

                            sql, params = self._build_insert_sql(
                                table_name, cols, batch
                            )
                            cursor.execute(sql, params)

                            # 批量更新进度 + 事务提交
                            if batch_idx % COMMIT_INTERVAL == 0:
                                pbar.update(COMMIT_INTERVAL)
                                conn.commit()

                        # 补齐最后零散批次
                        remain = batch_idx % COMMIT_INTERVAL
                        if remain > 0:
                            pbar.update(remain)

                    conn.commit()
                    logger.info(
                        f"[{table_name}] Big table done, total inserted: {total_rows}"
                    )

            except Exception as e:
                conn.rollback()
                logger.error(f"[{table_name}] Write failed, rollback: {str(e)}")
                raise
            finally:
                cursor.close()

    @property
    @abstractmethod
    def _db_prefix(self) -> str:
        """进度条前缀标识：[MySQL] / [PG]"""
        pass

    # 数据加载 公共方法
    @log_elapsed
    def load_author(self) -> None:
        self.author_df = pd.read_sql(text("SELECT * FROM author"), con=sqlite_engine)

    @log_elapsed
    def load_contest(self) -> None:
        self.contest_df = pd.read_sql(text("SELECT * FROM contest"), con=sqlite_engine)

    @log_elapsed
    def load_tag(self) -> None:
        self.tag_df = pd.read_sql(text("SELECT * FROM tag"), con=sqlite_engine)

    @log_elapsed
    def load_novel(self) -> None:
        self.novel_df = pd.read_sql(text("SELECT * FROM novel"), con=sqlite_engine)

    @log_elapsed
    def load_tag_link(self) -> None:
        self.tag_link_df = pd.read_sql(
            text("SELECT * FROM noveltaglink"), con=sqlite_engine
        )

    # 导出逻辑
    @log_elapsed
    def export_dim_tables(self) -> None:
        self._batch_write_table(self.tag_df, "tag")
        self._batch_write_table(self.contest_df, "contest")
        self._batch_write_table(self.author_df, "author")

    @log_elapsed
    def export_novel_table(self) -> None:
        self._batch_write_table(self.novel_df, "novel")

    @log_elapsed
    def export_tag_relation(self) -> None:
        if self.tag_link_df.empty:
            logger.warning("noveltaglink empty, skip write")
            return
        if self.incremental:
            novel_ids = self.tag_link_df["novel_id"].unique().tolist()
            if novel_ids:
                ph = ", ".join([f":n{i}" for i in range(len(novel_ids))])
                del_sql = f"DELETE FROM noveltaglink WHERE novel_id IN ({ph})"
                params = [f"n{i}" for i in range(len(novel_ids))]
                with Session(cloud_engine) as session:
                    session.exec(text(del_sql), params=params)
                    session.commit()
                logger.info("Old relation records deleted for incremental sync")
        self._batch_write_table(self.tag_link_df, "noveltaglink")

    @log_elapsed
    def process(self) -> None:
        logger.info(f"Start {self._db_type} Sync | Mode: {self.run_mode}")
        if self.run_mode == "full":
            self._clear_all_related_tables()

        self.load_tag()
        self.load_author()
        self.load_contest()
        self.load_novel()
        self.load_tag_link()

        self.export_dim_tables()
        self.export_novel_table()
        self.export_tag_relation()
        logger.info(f"{self._db_type} sync completed")

    @property
    @abstractmethod
    def _db_type(self) -> str:
        """数据库名称标识"""
        pass


class MySQLSyncDataset(BaseSyncDataset):
    """MySQL 同步子类，仅实现数据库差异化逻辑"""

    @property
    def _db_prefix(self) -> str:
        return "[MySQL]"

    @property
    def _db_type(self) -> str:
        return "MySQL"

    def _clear_all_related_tables(self) -> None:
        clear_sqls = [
            "SET FOREIGN_KEY_CHECKS = 0;",
            "TRUNCATE TABLE noveltaglink;",
            "TRUNCATE TABLE novel;",
            "TRUNCATE TABLE tag;",
            "TRUNCATE TABLE contest;",
            "TRUNCATE TABLE author;",
            "SET FOREIGN_KEY_CHECKS = 1;",
        ]
        with Session(cloud_engine) as session:
            for sql in clear_sqls:
                session.exec(text(sql))
            session.commit()
        logger.info("All remote tables truncated for full refresh")

    def _build_insert_sql(
        self, table_name: str, cols: list, batch: list
    ) -> tuple[str, list]:
        col_str = ", ".join(cols)
        row_fmt = ", ".join(["%s"] * len(cols))
        row_vals = [f"({row_fmt})" for _ in batch]
        sql = f"INSERT IGNORE INTO {table_name} ({col_str}) VALUES {','.join(row_vals)}"
        params = []
        for row in batch:
            params.extend(row)
        return sql, params


class PostgresSyncDataset(BaseSyncDataset):
    """PostgreSQL 同步子类，仅实现数据库差异化逻辑"""

    @property
    def _db_prefix(self) -> str:
        return "[PG]"

    @property
    def _db_type(self) -> str:
        return "PostgreSQL"

    def _clear_all_related_tables(self) -> None:
        clear_sql = "TRUNCATE TABLE noveltaglink, novel, tag, contest, author CASCADE;"
        with Session(cloud_engine) as session:
            session.exec(text(clear_sql))
            session.commit()
        logger.info("All remote Postgres tables truncated for full refresh")

    def _build_insert_sql(
        self, table_name: str, cols: list, batch: list
    ) -> tuple[str, list]:
        col_str = ", ".join(cols)
        bool_fields = TABLE_BOOL_COLS.get(table_name, [])

        # 构造带 ::boolean 类型转换的占位符
        placeholders = []
        for c in cols:
            if c in bool_fields:
                placeholders.append("%s::boolean")
            else:
                placeholders.append("%s")
        row_place = ", ".join(placeholders)
        row_vals = [f"({row_place})" for _ in batch]

        sql = (
            f"INSERT INTO {table_name} ({col_str}) VALUES {','.join(row_vals)} "
            f"ON CONFLICT DO NOTHING"
        )
        params = []
        for row in batch:
            params.extend(row)
        return sql, params


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 按需实例化对应数据库
    # sync_task = MySQLSyncDataset(run_mode="full")
    sync_task = PostgresSyncDataset(run_mode="full")
    sync_task.process()
