from typing import Any, Iterator, Type, Iterable

from sqlmodel import Session, select

from .database import create_db_and_tables, create_sqlite_engine
from .models import Author, Contest, Novel, NovelTagLink, Tag


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


def batch_insert_name(
    engine,
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


def create_name_records(engine, records: list[Any], chunk: int = 1000) -> None:
    """Create name records for Author table via chunked bulk insertion.

    Entry function for name-only simple tables.
    Complex relational tables use independent implementations.

    Args:
        engine: SQLAlchemy engine instance.
        records: List of name strings/values.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, records, Author, chunk_size=chunk)


def create_authors(engine, authors: list[str], chunk: int = 1000) -> None:
    """Create author records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        authors: List of author name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, authors, Author, chunk_size=chunk)


def create_contests(engine, contests: list[str], chunk: int = 1000) -> None:
    """Create contest records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        contests: List of contest name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, contests, Contest, chunk_size=chunk)


def create_tags(engine, tags: list[str], chunk: int = 1000) -> None:
    """Create tag records via chunked bulk insertion.

    Args:
        engine: SQLAlchemy engine instance.
        tags: List of tag name strings.
        chunk: Number of rows per single data chunk.
    """
    batch_insert_name(engine, tags, Tag, chunk_size=chunk)


def get_tag_map(engine) -> dict[str, int]:
    with Session(engine) as session:
        res = session.exec(select(Tag.name, Tag.id)).all()
        return {name: tid for name, tid in res}


def get_contest_map(engine) -> dict[str, int]:
    with Session(engine) as session:
        res = session.exec(select(Contest.name, Contest.id)).all()
        return {name: cid for name, cid in res}


def main():
    import pandas as pd
    from pathlib import Path

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


if __name__ == "__main__":
    main()
