"""Task table maintenance — requests + lxml

Usage:
    uv run python website/task_runner.py
    uv run python website/task_runner.py --limit 100
    uv run python website/task_runner.py --skip-fill

Two main APIs:
    fetch_html(session, nid) — detail page HTML → lxml → all fields
    fetch_api(session, nid)  — comment/review JSON API
"""

import argparse
import os
import sys
import time as time_mod
from datetime import datetime

import django
import lxml.html
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from novels.models import Task  # noqa: E402
from novels.mappings import GENRE, STATUS, PTYPE  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
COMMON_URL = "https://book.sfacg.com/ajax/ashx/Common.ashx"


# ---------------------------------------------------------------------------
# API 1: fetch_html — detail page HTML via lxml
# ---------------------------------------------------------------------------


def fetch_html(session, nid):
    """GET /Novel/{nid}/ → parse all fields with lxml.

    Reuses CSS selectors from meta.py (converted to XPath):
      .count-detail .text-row .text::text
      #BasicOperation .btn::text
      .title .tag::text
      .d-banner
      .tag-list .tag .highlight .text::text

    Also extracts title, author, cover from page structure.
    """
    url = f"https://book.sfacg.com/Novel/{nid}/"
    resp = session.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    tree = lxml.html.fromstring(resp.text)

    # Title from <h1>
    h1_texts = tree.xpath("//h1//text()")
    title = "".join(t.strip() for t in h1_texts)

    # Author from <title> tag
    # Format: '小说名 - 小说全文阅读 - 类型标签 - 作者 - SF轻小说'
    raw = tree.xpath("//title/text()")[0].strip()
    parts = [p.strip() for p in raw.split(" - ")]
    author_name = parts[-2] if len(parts) >= 3 else ""

    # Cover: first NovelCover image
    covers = tree.xpath('//img[contains(@src,"NovelCover")]/@src')
    cover = covers[0] if covers else None

    # Stats row: 类型/字数/人气/更新
    row = tree.xpath(
        '//div[contains(@class,"count-detail")]'
        '//div[contains(@class,"text-row")]'
        '//span[contains(@class,"text")]/text()'
    )
    # Buttons: 赞/收藏
    btns = tree.xpath(
        '//div[@id="BasicOperation"]' '//a[contains(@class,"btn")]/text()'
    )
    # Ptype + contest tags
    ptype_contest = tree.xpath(
        '//div[contains(@class,"title")]' '//span[contains(@class,"tag")]/text()'
    )
    # Banner
    banner = tree.xpath('//div[contains(@class,"d-banner")]')
    # Tags
    tags = tree.xpath(
        '//div[contains(@class,"tag-list")]'
        '//div[contains(@class,"tag")]'
        '//span[contains(@class,"highlight")]'
        '//span[contains(@class,"text")]/text()'
    )

    return {
        "title": title,
        "author": author_name,
        "cover": cover,
        "has_banner": bool(banner),
        "tags": tags,
        **_parse_row(row),
        **_parse_btns(btns),
        **_parse_ptype_contest(ptype_contest),
    }


# ---------------------------------------------------------------------------
# API 2: fetch_api — comment/review JSON
# ---------------------------------------------------------------------------


def fetch_api(session, nid):
    """GET Common.ashx?op=getcomment → JSON.

    Returns comment_num (short comments) and review_num (long reviews).
    """
    params = {
        "op": "getcomment",
        "nid": nid,
        "_": int(time_mod.time() * 1000),
    }
    resp = session.get(COMMON_URL, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "comment_num": data.get("ShortCommentNum"),
        "review_num": data.get("LongCommentNum"),
    }


# ---------------------------------------------------------------------------
# HTML parsing helpers (convert meta.py CSS selectors → XPath)
# ---------------------------------------------------------------------------


def _parse_row(row):
    """Parse genre, word_num, status, click_num, last_update.

    Example:
        ['类型：魔幻', '字数：3240533字[连载中]',
         '人气：4757.4万', '更新：2026/5/25 20:26:36']
    """
    if len(row) < 4:
        return {}
    values = [item.split("：")[-1] for item in row]
    genre, wordnum_status, click_num, last_update = values
    word_num, status = wordnum_status.split("字[")
    status = status.replace("]", "")
    click_num = click_num.replace("人气", "").replace("点击", "")
    return {
        "genre": genre,
        "word_num": int(word_num),
        "status": status,
        "click_num": int(
            click_num
            if "万" not in click_num
            else float(click_num.replace("万", "")) * 10_000
        ),
        "last_update": datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S"),
    }


def _parse_btns(btns):
    """Parse praise_num, like_num.

    Example: ['点击阅读', '赞 27872', '收藏 278629']
    """
    if len(btns) < 2:
        return {}
    praise_num, like_num = [int(btn.split(" ")[-1]) for btn in btns[-2:]]
    return {"praise_num": praise_num, "like_num": like_num}


def _parse_ptype_contest(ptype_contest):
    """Parse ptype, contest.

    Example: ['VIP', '第九届冬季征文'] or ['签约'] or []
    """
    ptypes = {"签约", "VIP"}
    ptype_contest = set(ptype_contest)
    ptype = ptypes & ptype_contest
    contest = ptype_contest - ptypes
    return {
        "ptype": "免费" if not ptype else ptype.pop(),
        "contest": "" if not contest else contest.pop(),
    }


# ---------------------------------------------------------------------------
# fill_tasks + run_tasks
# ---------------------------------------------------------------------------


def fill_tasks():
    """Call Django management command to populate Task table."""
    from django.core.management import call_command

    call_command("fill_tasks")


def run_tasks(limit=None):
    """Iterate Task table, fetch+update each novel, delete task."""
    from novels.models import Author, Contest, Tag

    session = requests.Session()
    tasks = Task.objects.select_related("novel").all()
    if limit:
        tasks = tasks[:limit]
    total = tasks.count() if limit is None else limit
    print(f"Processing {total} tasks ...")

    success = 0
    failed = 0
    for i, task in enumerate(tasks, 1):
        novel = task.novel
        try:
            html_data = fetch_html(session, novel.id)
            api_data = fetch_api(session, novel.id)
            data = {**html_data, **api_data}

            # Simple scalar fields
            for key in [
                "title",
                "word_num",
                "click_num",
                "praise_num",
                "like_num",
                "has_banner",
                "last_update",
                "comment_num",
                "review_num",
            ]:
                val = data.get(key)
                if val is not None:
                    setattr(novel, key, val)

            # Cover (skip default images)
            cover = data.get("cover")
            if cover and "defaultNew.jpg" not in cover:
                novel.cover = cover

            # Enum strings → int
            if data.get("status"):
                novel.status = STATUS.get_value(data["status"])
            if data.get("genre"):
                novel.genre = GENRE.get_value(data["genre"])
            if data.get("ptype"):
                novel.ptype = PTYPE.get_value(data["ptype"])

            # Author FK
            author_name = data.get("author")
            if author_name:
                author, _ = Author.objects.get_or_create(name=author_name)
                novel.author = author

            # Contest FK
            contest_name = data.get("contest")
            if contest_name:
                contest, _ = Contest.objects.get_or_create(name=contest_name)
                novel.contest = contest

            novel.save()

            # Tags M2M
            tag_names = data.get("tags", [])
            if tag_names:
                tag_objs = []
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tag_objs.append(tag)
                novel.tags.set(tag_objs)

            task.delete()
            success += 1
            print(f"  [{i}/{total}] Novel {novel.id} " f"updated, task deleted")
        except Exception as e:
            failed += 1
            print(f"  [{i}/{total}] Novel {novel.id} FAILED: {e}")

    remaining = Task.objects.count()
    print(f"Done. {success} updated, {failed} failed, " f"{remaining} tasks remaining.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task table maintenance")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of tasks to process",
    )
    parser.add_argument(
        "--skip-fill",
        action="store_true",
        help="Skip fill_tasks step",
    )
    args = parser.parse_args()

    if not args.skip_fill:
        fill_tasks()
    run_tasks(limit=args.limit)
