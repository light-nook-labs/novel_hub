"""清空本地和云端数据库（dev 阶段使用）。"""

from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import Engine

from database.engine import cloud_engine, sqlite_engine
from database.models import Author, Banner, Contest, Novel, NovelTagLink, Tag
from sqlmodel import Session


def reset():
    load_dotenv()
    # 删除本地 SQLite
    db_path = Path("database.db")
    sqlite_engine.dispose()
    if db_path.exists():
        db_path.unlink()
        print("SQLite deleted")
    else:
        print("SQLite not found, skip")

    # 清空云端（自动兼容 PostgreSQL / MySQL / SQLite）
    if cloud_engine is None:
        print("Cloud not configured, skip")
        return

    with Session(cloud_engine) as s:
        engine: Engine = cloud_engine
        dialect = engine.dialect.name

        # --------------------------
        # 🔥 跨数据库兼容：关闭外键约束
        # --------------------------
        try:
            if dialect == "postgresql":
                s.exec(text("SET session_replication_role = 'replica';"))
            elif dialect == "mysql":
                s.exec(text("SET FOREIGN_KEY_CHECKS = 0;"))
            elif dialect == "sqlite":
                s.exec(text("PRAGMA foreign_keys = OFF;"))

            # 按顺序删除表
            for t in [NovelTagLink, Banner, Novel, Contest, Author, Tag]:
                s.exec(t.__table__.delete())

        finally:
            # --------------------------
            # 🔥 恢复外键约束
            # --------------------------
            if dialect == "postgresql":
                s.exec(text("SET session_replication_role = 'origin';"))
            elif dialect == "mysql":
                s.exec(text("SET FOREIGN_KEY_CHECKS = 1;"))
            elif dialect == "sqlite":
                s.exec(text("PRAGMA foreign_keys = ON;"))

        s.commit()

    print("Cloud tables truncated")


if __name__ == '__main__':
    reset()