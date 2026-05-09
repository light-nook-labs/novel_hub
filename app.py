from database import SQLModel, engine


def create_db_and_table():
    SQLModel.metadata.create_all(engine)


if __name__ == '__main__':
    create_db_and_table()