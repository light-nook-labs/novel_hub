from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str


class Tag(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str