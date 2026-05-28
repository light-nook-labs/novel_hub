from pathlib import Path
from typing import Any, Iterator, Type

from sqlmodel import Session, select, text, inspect, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError

from .database import create_db_and_tables, create_sqlite_engine
from .models import Author, Contest, Novel, NovelTagLink, Tag

############
# Iterator #
############


def iter_chunks(seq: list[Any], chunk_size: int = 1000) -> Iterator[range]:
    """Yield index ranges for chunked iteration over a sequence.

    Uses pure index ranges to avoid creating sublist copies,
    which optimizes memory usage for large datasets.

    Args:
        seq: Original list to be split into chunks.
        chunk_size: Maximum number of items per single chunk.

    Yields:
        Range object containing start and end indices of each chunk.
    """
    total_length = len(seq)
    for start in range(0, total_length, chunk_size):
        end = start + chunk_size
        yield range(start, min(end, total_length))


##########
# Create #
##########


def batch_insert_name(
    engine: Engine,
    name_list: list[Any],
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
    with Session(engine) as session:
        for index_range in iter_chunks(name_list, chunk_size):
            # Build model instances for current chunk
            instances = (model(name=name_list[idx]) for idx in index_range)
            session.add_all(instances)
            # Commit per chunk for rollback support
            session.commit()


def create_name_records(engine: Engine, records: list[Any], chunk: int = 1000) -> None:
    """Create name records for Author table via chunked bulk insertion.

    Entry function for name-only simple tables.
    Complex relational tables use independent implementations.

    Args:
        engine: SQLAlchemy engine instance.
        records: List of name strings/values.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, records, Author, chunk_size=chunk)


def create_authors(engine: Engine, authors: list[str], chunk: int = 1000) -> None:
    """Create author records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        authors: List of author name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, authors, Author, chunk_size=chunk)


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
            return 0


##########
# Delete #
##########


def drop_all(engine: Engine, is_keep_tables: bool = True) -> list[str]:
    """Clear all data in database tables.

    Different operations are applied based on database dialect and is_keep_tables flag:
    - SQLite: Delete the entire database file directly.
    - MySQL: If is_keep_tables is True, truncate each table; if False, drop each table.
    - PostgreSQL: If is_keep_tables is True, truncate tables and reset identity;
    if False, drop tables with cascade.

    Args:
        engine: SQLAlchemy engine instance.
        is_keep_tables: If True, keep table structure and only clear data;
                    If False, drop the tables entirely.

    Returns:
        list[str]: List of all table names processed.
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    dialect_name = engine.dialect.name

    if dialect_name == "sqlite":
        db_path = engine.url.database
        engine.dispose()
        if db_path:
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink(missing_ok=True)
    else:
        with Session(engine) as session:
            if dialect_name == "mysql":
                session.exec(text("SET FOREIGN_KEY_CHECKS = 0;"))
                for table in all_tables:
                    if is_keep_tables:
                        session.exec(text(f"TRUNCATE TABLE `{table}`;"))
                    else:
                        session.exec(text(f"DROP TABLE IF EXISTS `{table}`;"))
                session.exec(text("SET FOREIGN_KEY_CHECKS = 1;"))
            elif dialect_name == "postgresql":
                if all_tables:
                    tables_str = ", ".join(all_tables)
                    if is_keep_tables:
                        session.exec(
                            text(f"TRUNCATE {tables_str} RESTART IDENTITY CASCADE;")
                        )
                    else:
                        session.exec(
                            text(f"DROP TABLE IF EXISTS {tables_str} CASCADE;")
                        )
            session.commit()

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
    from .database import cloud_engine

    def main():

        engine = create_sqlite_engine(filename="test.db")
        create_db_and_tables(engine)

        # 使用 pathlib 读取 JSONL 文件，添加 lines=True 适配行式JSON
        data_path = Path("o.jsonl")
        df = pd.read_json(data_path, lines=True)

        # 提取并导入作者（去重）
        author_list = df["author"].drop_duplicates().tolist()
        create_authors(engine, author_list)

        # 提取并导入征文（去重 + 过滤空值）
        contest_series = df["contest"].drop_duplicates().str.strip()
        contest_list = contest_series[contest_series != ""].tolist()
        create_contests(engine, contest_list)

        # 提取并导入标签（拆分列表、去重、过滤空值）
        tag_series = df.explode("tags")["tags"].drop_duplicates().dropna().str.strip()
        tag_list = tag_series.tolist()
        create_tags(engine, tag_list)

    # engine = create_sqlite_engine(filename="test.db")
    engine = cloud_engine
    create_db_and_tables(engine)
    m = get_max_author_id(engine)
    print(m)

    res = drop_all(engine, is_keep_tables=False)
    print(res)

    m = get_max_author_id(engine)
    print(m)
