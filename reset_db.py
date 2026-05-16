"""清空本地和云端数据库（dev 阶段使用）。"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from database.engine import cloud_engine, sqlite_engine
from database.models import Author, Banner, Contest, Novel, NovelTagLink, Tag
from sqlmodel import Session

# 删除本地 SQLite
db_path = Path("database.db")
sqlite_engine.dispose()
if db_path.exists():
    db_path.unlink()
    print("SQLite deleted")
else:
    print("SQLite not found, skip")

# 清空云端
if cloud_engine is None:
    print("Cloud not configured, skip")
else:
    with Session(cloud_engine) as s:
        for t in [NovelTagLink, Banner, Novel, Contest, Author, Tag]:
            s.exec(t.__table__.delete())
        s.commit()
    print("Cloud tables truncated")
