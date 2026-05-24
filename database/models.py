"""
ORM
"""


from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

####################
# Conjuction Table #
####################


class NovelTagLink(SQLModel, table=True):
    tag_id: int | None = Field(
        default=None, foreign_key="tag.id", primary_key=True
    )
    novel_id: int | None = Field(
        default=None, foreign_key="novel.id", primary_key=True
    )


#########
# Table #
#########


class Author(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(unique=True)

    novels: list["Novel"] = Relationship(
        back_populates="author", passive_deletes="all"
    )


class Tag(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(unique=True)

    novels: list["Novel"] = Relationship(
        back_populates="tags", link_model=NovelTagLink
    )


class Contest(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(unique=True)

    novels: list["Novel"] = Relationship(
        back_populates="contest", passive_deletes="all"
    )


##############
# Main Table #
##############


class Novel(SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str
    ptype: int | None = Field(default=None, index=True)
    genre: int | None = Field(default=None, index=True)
    status: int | None = Field(default=None, index=True)
    click_num: int | None = None
    word_num: int | None = None
    praise_num: int | None = None
    like_num: int | None = None
    cover: str | None = None

    last_update: datetime | None = None
    db_update: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
    )

    # Relationship

    # Foreign Key: Author(1) Novel(n)
    author_id: int | None = Field(
        default=None, foreign_key="author.id", ondelete="SET NULL"
    )
    author: Author | None = Relationship(back_populates="novels")

    # Foreign Key: Contest(1) Novel(n)
    contest_id: int | None = Field(
        default=None, foreign_key="contest.id", ondelete="SET NULL"
    )
    contest: Contest | None = Relationship(back_populates="novels")

    # Many to many: Novel(m) Tag(n)
    tags: list[Tag] = Relationship(
        back_populates="novels", link_model=NovelTagLink
    )
