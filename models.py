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
    has_banner: bool
    word_num: int | None
    click_num: int | None
    praise_num: int | None
    like_num: int | None
    ptype: str
    contest: str
    last_update: datetime | None = None
    review_num: int | None
    comment_num: int | None
    tags: list[str] = []
    cover: str = ""


__all__ = ["Meta"]
