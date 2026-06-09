"""fetch_api — comment/review JSON API."""

import time

from .config import COMMON_URL, HEADERS


def fetch_api(session, nid):
    """GET Common.ashx?op=getcomment → JSON.

    Returns comment_num (short comments) and review_num (long reviews).
    """
    params = {
        "op": "getcomment",
        "nid": nid,
        "_": int(time.time() * 1000),
    }
    resp = session.get(COMMON_URL, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "comment_num": data.get("ShortCommentNum"),
        "review_num": data.get("LongCommentNum"),
    }
