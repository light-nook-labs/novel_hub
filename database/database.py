"""
Engine
Create DB and Tabel
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel
from sqlmodel import text as sql_text

load_dotenv()

# Global constants
PROD_SQLITE_FILE = "database.db"
BASE_DIR = Path(__file__).resolve().parent.parent

##########
# SQLite #
##########

sqlite_db_path = BASE_DIR / PROD_SQLITE_FILE
sqlite_url = f"sqlite:///{sqlite_db_path}"

sqlite_engine = create_engine(sqlite_url, echo=False)


def create_sqlite_engine(filename: str, echo: bool = True):
    """Create a SQLite database engine for development usage.

    Production database file is prohibited to avoid accidental data overwrite.

    Args:
        filename: Name of the target SQLite database file.
        echo: If True, enable SQL statement logging. Defaults to True.

    Returns:
        sqlalchemy.engine.Engine: Configured SQLite engine instance.

    Raises:
        ValueError: When input filename equals production database filename.
    """
    if filename == PROD_SQLITE_FILE:
        raise ValueError(
            f"{PROD_SQLITE_FILE} is reserved for production, cannot use for development."
        )
    db_path = BASE_DIR / filename
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url, echo=echo)


#########
# Cloud #
#########

DB_TYPE = os.getenv("DB_TYPE", "").strip().lower()
DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_NAME = os.getenv("DB_NAME", "").strip()

cloud_engine = None
required_cloud_vars = [DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]

if all(required_cloud_vars):
    try:
        port = int(DB_PORT)
        if DB_TYPE == "mysql":
            driver = "mysql+pymysql"
        elif DB_TYPE == "postgresql":
            driver = "postgresql"
        else:
            raise ValueError(
                f"Unsupported database type: {DB_TYPE}. Use mysql or postgresql."
            )

        # Fix: Embed username & password into connection URL (standard usage)
        cloud_url = f"{driver}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{port}/{DB_NAME}"
        cloud_engine = create_engine(
            cloud_url, pool_size=5, max_overflow=5, pool_pre_ping=True
        )
    except (ValueError, Exception) as e:
        print(f"[Warning] Failed to initialize cloud database engine: {str(e)}")


#####################
# Init DB and Table #
#####################


def create_db_and_tables(engine):
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


__all__ = [
    "sqlite_engine",
    "cloud_engine",
    "create_sqlite_engine",
    "create_db_and_tables",
]

if __name__ == "__main__":
    print(sqlite_engine)
    print(cloud_engine)
