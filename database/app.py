"""
Create database and tables
"""


from . import SQLModel


def create_db_and_table(engine):
    SQLModel.metadata.create_all(engine)
