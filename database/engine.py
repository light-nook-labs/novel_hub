from sqlmodel import create_engine, SQLModel

##########
# SQLite #
##########

sqlite_file_name = 'database.db'
sqlite_url = f'sqlite:///{sqlite_file_name}'

sqlite_engine = create_engine(sqlite_url, echo=False)


############
# Postgres #
############

# postgres_engine = create_engine("postgresql://scott:tiger@localhost:5432/mydatabase")