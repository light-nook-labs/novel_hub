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


############
# Postgres #
############

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")

pg_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

postgres_engine = create_engine(pg_url, echo=False)
