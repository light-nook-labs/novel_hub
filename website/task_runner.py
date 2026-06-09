"""Task table maintenance — requests + lxml

Usage:
    uv run python website/task_runner.py
    uv run python website/task_runner.py --limit 100
    uv run python website/task_runner.py --skip-fill

Pipeline:
1. fill_tasks — populate Task table with novels that have duplicate covers
2. run_tasks  — re-scrape each Task's novel, update DB, delete Task
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
COMMON_URL = "https://book.sfacg.com/ajax/ashx/Common.ashx"


def fill_tasks():
    """Call Django management command to populate Task table."""
    from django.core.management import call_command

    call_command("fill_tasks")


def fetch_detail(session, nid):
    """GET /Novel/{nid}/ — parse HTML with lxml (reusing meta.py selectors).

    CSS selectors from meta.py → XPath equivalents:
      .count-detail .text-row .text::text
      #BasicOperation .btn::text
      .title .tag::text
      .d-banner
      .tag-list .tag .highlight .text::text
    """
    url = f"https://book.sfacg.com/Novel/{nid}/"
    headers = {"User-Agent": USER_AGENT}
    resp = session.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    tree = lxml.html.fromstring(resp.text)

    row = tree.xpath(
        '//div[contains(@class,"count-detail")]'
        '//div[contains(@class,"text-row")]'
        '//span[contains(@class,"text")]/text()'
    )
    btns = tree.xpath(
        '//div[@id="BasicOperation"]' '//a[contains(@class,"btn")]/text()'
    )
    ptype_contest = tree.xpath(
        '//div[contains(@class,"title")]' '//span[contains(@class,"tag")]/text()'
    )
    banner = tree.xpath('//div[contains(@class,"d-banner")]')
    tags = tree.xpath(
        '//div[contains(@class,"tag-list")]'
        '//div[contains(@class,"tag")]'
        '//span[contains(@class,"highlight")]'
        '//span[contains(@class,"text")]/text()'
    )

    return {
        "has_banner": bool(banner),
        "tags": tags,
        **parse_row(row),
        **parse_btns(btns),
        **parse_ptype_contest(ptype_contest),
    }


def fetch_comment(session, nid):
    """GET Common.ashx?op=getcomment — JSON API."""
    headers = {"User-Agent": USER_AGENT}
    params = {"op": "getcomment", "nid": nid, "_": int(time_mod.time() * 1000)}
    resp = session.get(COMMON_URL, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "comment_num": data.get("ShortCommentNum"),
        "review_num": data.get("LongCommentNum"),
    }


def parse_row(row):
    """Parse word_num, status, click_num, last_update.

    Example row:
        ['类型：魔幻', '字数：3240533字[连载中]',
         '点击：4757.4万', '更新：2026/5/25 20:26:36']
    """
    if len(row) < 4:
        return {}
    values = [item.split("：")[-1] for item in row]
    _, wordnum_status, click_num, last_update = values
    word_num, status = wordnum_status.split("字[")
    status = status.replace("]", "")
    return {
        "word_num": int(word_num),
        "status": status,
        "click_num": int(
            click_num
            if "万" not in click_num
            else float(click_num.replace("万", "")) * 10_000
        ),
        "last_update": datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S"),
    }


def parse_btns(btns):
    """Parse praise_num, like_num from buttons.

    Example: ['点击阅读', '赞 27872', '收藏 278629']
    """
    if len(btns) < 2:
        return {}
    praise_num, like_num = [int(btn.split(" ")[-1]) for btn in btns[-2:]]
    return {"praise_num": praise_num, "like_num": like_num}


def parse_ptype_contest(ptype_contest):
    """Parse ptype, contest from tags.

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


def run_tasks(limit=None):
    """Iterate Task table, fetch+update each novel, delete task."""
    from novels.models import Author, Tag

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
            detail = fetch_detail(session, novel.id)
            comment = fetch_comment(session, novel.id)

            # Update simple fields
            for key in [
                "word_num",
                "click_num",
                "praise_num",
                "like_num",
                "has_banner",
                "last_update",
                "comment_num",
                "review_num",
            ]:
                val = {**detail, **comment}.get(key)
                if val is not None:
                    setattr(novel, key, val)

            # Convert enum strings to int
            if detail.get("status"):
                novel.status = STATUS.get_value(detail["status"])
            if detail.get("genre"):
                novel.genre = GENRE.get_value(detail["genre"])
            if detail.get("ptype"):
                novel.ptype = PTYPE.get_value(detail["ptype"])

            # Handle author FK
            author_name = detail.get("author")
            if author_name:
                author, _ = Author.objects.get_or_create(name=author_name)
                novel.author = author

            novel.save()

            # Handle tags M2M
            tag_names = detail.get("tags", [])
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
