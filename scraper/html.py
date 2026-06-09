"""fetch_html — detail page HTML via lxml.

Reuses CSS selectors from meta.py (converted to XPath):
  .count-detail .text-row .text::text
  #BasicOperation .btn::text
  .title .tag::text
  .d-banner
  .tag-list .tag .highlight .text::text
"""

from datetime import datetime

import lxml.html

from .config import HEADERS, NOVEL_URL


def fetch_html(session, nid):
    """GET /Novel/{nid}/ → parse all fields with lxml."""
    url = NOVEL_URL.format(nid=nid)
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

    # Stats row
    row = tree.xpath(
        '//div[contains(@class,"count-detail")]'
        '//div[contains(@class,"text-row")]'
        '//span[contains(@class,"text")]/text()'
    )
    # Buttons
    btns = tree.xpath(
        '//div[@id="BasicOperation"]' '//a[contains(@class,"btn")]/text()'
    )
    # Ptype + contest
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
