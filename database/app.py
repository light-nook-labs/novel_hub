from pathlib import Path
from typing import Any, Iterator, Type

from sqlmodel import Session, select, text, inspect, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from .database import create_db_and_tables
from .models import Author, Contest, Tag
from . import logger

############
# Iterator #
############


def iter_chunks(seq: list[Any], chunk_size: int = 1000) -> Iterator[list[Any]]:
    """Yield sliced sublist for chunked iteration."""
    total_length = len(seq)
    for start in range(0, total_length, chunk_size):
        end = start + chunk_size
        yield seq[start:end]


##########
# Create #
##########


def batch_insert_name(
    engine: Engine,
    name_list: list[str],
    model: Type[Tag | Contest | Author],
    chunk_size: int = 1000,
) -> None:
    """Bulk insert name field records for simple tables in chunks.

    Use session.add_all() for batch adding. Commit after each single chunk
    to support transaction rollback.
    All target tables only contain a basic `name` field.
    Complex tables with relationships are handled by other functions.
    Lazy iteration is used to eliminate extra list copies.

    Args:
        engine: SQLAlchemy engine instance.
        name_list: List of name values to insert.
        model: Target SQLModel class for simple name table.
        chunk_size: Number of rows per single data chunk.
    """
    if not name_list:
        logger.info(f"{model.__tablename__}: empty input list, skip insertion")
        return

    with Session(engine) as session:
        for chunk in iter_chunks(name_list, chunk_size):
            try:
                instances = [model(name=name) for name in chunk]
                session.add_all(instances)
                session.commit()
                logger.debug(f"{model.__tablename__}: inserted {len(chunk)} records")
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"{model.__tablename__}: insertion failed: {str(e)}")
                raise


def create_authors(
    engine: Engine, authors: list[dict[int, str]], chunk: int = 1000
) -> None:
    """Create author records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        authors: List of author name strings.
        chunk: Number of rows per single data chunk.
    """
    if not authors:
        logger.info(f"{Author.__tablename__}: empty input list, skip insertion")
        return

    with Session(engine) as session:
        for chunk in iter_chunks(authors, chunk):
            try:
                instances = [Author(**item) for item in chunk]
                session.add_all(instances)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"{Author.__tablename__}: insertion failed: {str(e)}")
                raise


def create_contests(engine: Engine, contests: list[str], chunk: int = 1000) -> None:
    """Create contest records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        contests: List of contest name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, contests, Contest, chunk_size=chunk)


def create_tags(engine: Engine, tags: list[str], chunk: int = 1000) -> None:
    """Create tag records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        tags: List of tag name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, tags, Tag, chunk_size=chunk)


############
# Retrieve #
############


def get_tag_map(engine: Engine) -> dict[str, int]:
    with Session(engine) as session:
        res = session.exec(select(Tag.name, Tag.id)).all()
        return {name: tid for name, tid in res}


def get_contest_map(engine: Engine) -> dict[str, int]:
    with Session(engine) as session:
        res = session.exec(select(Contest.name, Contest.id)).all()
        return {name: cid for name, cid in res}


def get_max_author_id(engine: Engine) -> int:
    with Session(engine) as session:
        try:
            statement = select(func.coalesce(func.max(Author.id), 0))
            result = session.exec(statement).first()
            return result if result is not None else 0
        except ProgrammingError:
            logger.warning("Author table not found, return max id 0")
            return 0


##########
# Delete #
##########


def drop_all(engine: Engine, is_keep_tables: bool = True) -> list[str]:
    """
    Clear data or drop all tables.
    SQLite: directly remove database file for testing.
    MySQL / PostgreSQL: use standard SQL statements.
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    dialect = engine.dialect.name

    if dialect == "sqlite":
        db_path = engine.url.database
        engine.dispose()
        if db_path:
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink(missing_ok=True)
                logger.info(f"SQLite database file {db_file.name} removed")
        return all_tables

    with Session(engine) as session:
        try:
            if dialect == "mysql":
                session.exec(text("SET FOREIGN_KEY_CHECKS = 0;"))
                for table in all_tables:
                    if is_keep_tables:
                        session.exec(text(f"TRUNCATE TABLE `{table}`;"))
                    else:
                        session.exec(text(f"DROP TABLE IF EXISTS `{table}`;"))
                session.exec(text("SET FOREIGN_KEY_CHECKS = 1;"))

            elif dialect == "postgresql":
                if all_tables:
                    table_quotes = ", ".join(f'"{t}"' for t in all_tables)
                    if is_keep_tables:
                        session.exec(
                            text(f"TRUNCATE {table_quotes} RESTART IDENTITY CASCADE;")
                        )
                    else:
                        session.exec(
                            text(f"DROP TABLE IF EXISTS {table_quotes} CASCADE;")
                        )

            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Table cleanup failed: {str(e)}")
            raise

    return all_tables


__all__ = [
    "iter_chunks",
    "create_authors",
    "create_contests",
    "create_tags",
    "get_tag_map",
    "get_contest_map",
    "get_max_author_id",
    "drop_all",
]


if __name__ == "__main__":
    import pandas as pd
    from .database import cloud_engine, create_sqlite_engine

    def main():
        CHUNK_SIZE = 1000
        data_file = Path("o.jsonl")
        # engine = create_sqlite_engine(filename="test.db")
        engine = cloud_engine

        create_db_and_tables(engine)

        if not data_file.exists():
            logger.error(f"文件 {data_file} 不存在，程序退出")
            return

        df = pd.read_json(data_file, lines=True)
        logger.info(f"成功读取数据源，总行数：{len(df)}")

        # 作者：构造字典列表
        author_data = df["author"].dropna().str.strip()
        author_list = author_data[author_data != ""].drop_duplicates().tolist()
        author_dict_list = [{"name": name} for name in author_list]
        create_authors(engine, author_dict_list, chunk=CHUNK_SIZE)
        logger.info(f"作者表导入完成，有效数据：{len(author_list)} 条")

        # 征文
        contest_data = df["contest"].dropna().str.strip()
        contest_list = contest_data[contest_data != ""].drop_duplicates().tolist()
        create_contests(engine, contest_list, chunk=CHUNK_SIZE)
        logger.info(f"征文表导入完成，有效数据：{len(contest_list)} 条")

        # 标签
        tag_data = df.explode("tags")["tags"].dropna().str.strip()
        tag_list = tag_data[tag_data != ""].drop_duplicates().tolist()
        create_tags(engine, tag_list, chunk=CHUNK_SIZE)
        logger.info(f"标签表导入完成，有效数据：{len(tag_list)} 条")

        logger.info("全部数据导入任务结束")

    main()
