from sqlmodel import SQLModel, Field, Session, create_engine


class Tag(SQLModel):
    id: int|None = Field(default=None, primary_key=True)
    name: str