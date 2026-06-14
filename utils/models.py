"""Shared Pydantic models for meta_spider and website."""

from datetime import datetime

from pydantic import BaseModel


class Meta(BaseModel):
    """Novel metadata from sfacg.com.

    Field names match JSONL/CSV files. Use to_django_dict() / from_django_dict()
    for Django ORM conversion.
    """

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
    review_num: int | None = None
    tags: list[str] = []
    cover: str | None = None

    def to_django_dict(self) -> dict:
        """Convert to Django model field names and types.

        Returns dict with:
        - nid → id
        - author → author_name (for FK lookup)
        - contest → contest_name (for FK lookup)
        - genre/status/ptype → integer enum values
        - cover → compressed suffix (default cover → None)
        """
        from .config import COVER_PREFIX, DEFAULT_COVER
        from .mappings import GENRE, STATUS, PTYPE

        # Compress cover URL
        cover = self.cover
        if cover and cover.startswith(COVER_PREFIX):
            suffix = cover[len(COVER_PREFIX) :]
            cover = None if suffix == DEFAULT_COVER else suffix

        return {
            "id": self.nid,
            "title": self.title,
            "author_name": self.author,
            "contest_name": self.contest,
            "genre": GENRE.get_value(self.genre),
            "status": STATUS.get_value(self.status),
            "ptype": PTYPE.get_value(self.ptype),
            "has_banner": self.has_banner,
            "word_num": self.word_num,
            "click_num": self.click_num,
            "praise_num": self.praise_num,
            "like_num": self.like_num,
            "comment_num": self.comment_num,
            "last_update": self.last_update,
            "review_num": self.review_num,
            "tags": self.tags,
            "cover": cover,
        }

    @classmethod
    def from_django_dict(cls, data: dict) -> "Meta":
        """Create from Django model dict (e.g. QuerySet.values()).

        Expects:
        - id (not nid)
        - author__name (not author)
        - contest__name (not contest)
        - genre/status/ptype as integer values
        - cover as compressed suffix
        """
        from .config import COVER_PREFIX
        from .mappings import GENRE, STATUS, PTYPE

        # Expand cover suffix to full URL
        cover = data.get("cover")
        if cover and not cover.startswith("http"):
            cover = COVER_PREFIX + cover

        return cls(
            nid=data["id"],
            title=data["title"],
            author=data.get("author__name") or "",
            genre=GENRE.get_zh(data.get("genre", 1)),
            status=STATUS.get_zh(data.get("status", 1)),
            ptype=PTYPE.get_zh(data.get("ptype", 1)),
            has_banner=data.get("has_banner"),
            word_num=data.get("word_num"),
            click_num=data.get("click_num"),
            praise_num=data.get("praise_num"),
            like_num=data.get("like_num"),
            comment_num=data.get("comment_num"),
            contest=data.get("contest__name"),
            last_update=data.get("last_update"),
            review_num=data.get("review_num"),
            tags=data.get("tags", []),
            cover=cover,
        )


__all__ = ["Meta"]
