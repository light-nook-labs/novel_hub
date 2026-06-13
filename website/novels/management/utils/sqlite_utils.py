"""SQLite bulk operations utilities.

Optimizations applied:
- WAL journal mode for concurrent reads during writes
- synchronous=NORMAL for faster writes (safe with WAL)
- Large batch sizes to reduce transaction overhead
- PRAGMA optimize at end for query planner
"""

from django.db import connection

from novels.models import Novel, Author, Tag, Contest

from . import int_or_none


def enable_wal_mode():
    """Enable WAL journal mode and tune SQLite for bulk operations."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")


def optimize():
    """Run PRAGMA optimize for query planner statistics."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA optimize")


def bulk_create_authors(authors, batch_size):
    """Bulk create authors and return {name: id} map."""
    Author.objects.bulk_create(
        [Author(name=a) for a in authors],
        batch_size=batch_size,
        ignore_conflicts=True,
    )
    return {a.name: a.id for a in Author.objects.all()}


def bulk_create_contests(contests, batch_size):
    """Bulk create contests and return {name: id} map."""
    Contest.objects.bulk_create(
        [Contest(name=c) for c in contests],
        batch_size=batch_size,
        ignore_conflicts=True,
    )
    return {c.name: c.id for c in Contest.objects.all()}


def bulk_create_tags(tags, batch_size):
    """Bulk create tags and return {name: id} map."""
    Tag.objects.bulk_create(
        [Tag(name=t) for t in tags],
        batch_size=batch_size,
        ignore_conflicts=True,
    )
    return {t.name: t.id for t in Tag.objects.all()}


def bulk_create_novels(df, author_map, contest_map, batch_size):
    """Bulk create novels from DataFrame."""
    novel_objs = []
    for row in df.itertuples(index=False):
        novel_objs.append(
            Novel(
                id=int(row.nid),
                title=row.novel_title if not is_na(row.novel_title) else "",
                ptype=int(row.ptype),
                genre=int(row.genre),
                status=int(row.status),
                click_num=int_or_none(row.click_num),
                word_num=int_or_none(row.word_num),
                praise_num=int_or_none(row.praise_num),
                like_num=int_or_none(row.like_num),
                review_num=int_or_none(getattr(row, "review_num", 0)),
                comment_num=int_or_none(getattr(row, "comment_num", 0)),
                has_banner=bool(row.banner),
                cover=row.cover,
                last_update=row.last_update if not is_na(row.last_update) else None,
                author_id=int(row.author_id) if not is_na(row.author_id) else None,
                contest_id=int(row.contest_id) if not is_na(row.contest_id) else None,
            )
        )
    Novel.objects.bulk_create(novel_objs, batch_size=batch_size, ignore_conflicts=True)
    del novel_objs


def bulk_insert_tags(tag_rows):
    """Bulk insert M2M tag relationships."""
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT OR IGNORE INTO novels_novel_tags (novel_id, tag_id) VALUES (?, ?)",
            tag_rows,
        )


def is_na(val):
    """Check if value is NA."""
    import pandas as pd

    return pd.isna(val)
