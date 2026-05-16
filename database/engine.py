import os

from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel

load_dotenv()

##########
# SQLite #
##########

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

sqlite_engine = create_engine(sqlite_url, echo=False)

# WAL 模式提升并发写入性能
from sqlmodel import text as sql_text

with sqlite_engine.connect() as conn:
    conn.execute(sql_text("PRAGMA journal_mode=WAL"))
    conn.commit()


#########
# Cloud #
#########

DB_TYPE = os.getenv("DB_TYPE", "").lower()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

_cloud_vars = [DB_HOST, DB_PORT, DB_USER, DB_NAME]

if all(_cloud_vars):
    if DB_TYPE == "mysql":
        cloud_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        cloud_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    cloud_engine = create_engine(cloud_url, echo=False)
else:
    cloud_engine = None
