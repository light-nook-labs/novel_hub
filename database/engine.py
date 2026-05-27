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
    cloud_engine = create_engine(cloud_url, pool_size=5, max_overflow=5)
else:
    cloud_engine = None


__all__ = ["SQLModel", "sqlite_engine", "cloud_engine"]


if __name__ == "__main__":
    print("sqlite" in str(sqlite_engine))
    print(cloud_engine)
