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

    def to_jsonl_dict(self) -> dict:
        """Convert to JSONL dict format (matches dataset/data/ schema)."""
        return {
            "nid": self.nid,
            "novel_title": self.title,
            "author": self.author,
            "price_type": self.ptype,
            "contest": self.contest,
            "genre": self.genre,
            "click_num": self.click_num,
            "word_num": self.word_num,
            "status": self.status,
            "last_update": (
                self.last_update.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_update
                else None
            ),
            "praise_num": self.praise_num,
            "like_num": self.like_num,
            "review_num": self.review_num,
            "comment_num": self.comment_num,
            "cover": self.cover,
            "banner": self.has_banner,
            "tags": self.tags,
        }


__all__ = ["Meta"]
