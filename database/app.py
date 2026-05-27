"""
Create database and tables
"""

from . import SQLModel
from sqlmodel import text as sql_text


def create_db_and_table(engine):
    """Create database and all defined tables.

    Enable WAL (Write-Ahead Logging) mode for SQLite to improve concurrency performance.

    Args:
        engine: SQLAlchemy database engine instance.
    """
    SQLModel.metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            conn.execute(sql_text("PRAGMA journal_mode=WAL"))
            conn.commit()


__all__ = ["create_db_and_table"]
