"""Shared Pydantic models for meta_spider and website."""

from datetime import datetime

from pydantic import BaseModel


class Meta(BaseModel):
    """Novel metadata from sfacg.com."""

    nid: int
    title: str
    author: str
    genre: str
    status: str
    ptype: str
    has_banner: bool | None = None
    word_num: int | None = None
    click_num: int | None = None
    praise_num: int | None = None
    like_num: int | None = None
    comment_num: int | None = None
    contest: str | None = None
    last_update: datetime | None = None
    review_num: int | None
    comment_num: int | None
    tags: list[str] = []
    cover: str | None = None


__all__ = ["Meta"]
