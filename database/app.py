"""
Create database and tables
"""

from . import SQLModel
from sqlmodel import text as sql_text


def create_db_and_table(engine):
    SQLModel.metadata.create_all(engine)
    if "sqlite" in str(engine):
        with engine.connect() as conn:
            conn.execute(sql_text("PRAGMA journal_mode=WAL"))
            conn.commit()


__all__ = ["create_db_and_table"]
