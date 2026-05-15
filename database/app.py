from . import SQLModel, sqlite_engine


def create_db_and_table(engine):
    SQLModel.metadata.create_all(engine)


if __name__ == '__main__':
    create_db_and_table(sqlite_engine)