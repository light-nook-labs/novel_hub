from sqlmodel import SQLModel, Field, Session, create_engine


class Novel(SQLModel, table=True):
    id: int|None = Field(default=None, primary_key=True)
    nid: int
    title: str
    like_num: int
    praise_num: int
    cover: str
    banner: str

    author: str|None = Field(foreign_key=True)
    price_type: None
    contest: str|None = Field(foreign_key=True)
    tag: str|None