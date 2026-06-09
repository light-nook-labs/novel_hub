# ============================================================================
# LEGACY SPIDER — commented out for reference
# Original implementation preserved below. See meta_batch.py for refactored version.
# Rules:
#   - DO NOT delete this code
#   - DO NOT modify CSS selectors/xpaths
#   - New code goes in meta_batch.py
# ============================================================================

# from datetime import datetime
# from time import time
# from typing import Any
# from urllib.parse import urlencode, urljoin
#
# from scrapy import Spider, Request
# from scrapy.exceptions import CloseSpider
# from scrapy.http import HtmlResponse, JsonResponse
# import requests
#
# from ..models import Meta
#
#
# class MetaSpider(Spider):
#     # scrapy shell "https://book.sfacg.com/List/default.aspx?PageIndex=1"
#     name = "meta"
#     allowed_domains = ["book.sfacg.com"]
#     _base_url = "https://book.sfacg.com/List/default.aspx"
#     _common_url = "https://book.sfacg.com/ajax/ashx/Common.ashx"
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.session = requests.Session()
#
#     async def start(self):
#         """CLI Args
#
#         Args:
#             begin: start page
#             num: total num
#
#         Examples:
#             - scrapy crawl meta -o o.jsonl -a num=3
#             - scrapy crawl meta -o o.jsonl -a num=3 -a begin=22
#             - scrapy crawl meta -o o.jsonl -a begin=12465
#         """
#         self.begin_num = int(getattr(self, "begin", 1))
#         self.curr_page = self.begin_num
#         self.total_num = int(getattr(self, "num", 2))
#         self.end_page = self.begin_num + self.total_num - 1
#
#         yield Request(self._join_url(), callback=self.parse)
#
#     def parse_detail(self, response: HtmlResponse, meta_info: dict[str, Any]):
#         # print(meta_info)
#         row = response.css(".count-detail .text-row .text::text").getall()
#         btns = response.css("#BasicOperation .btn::text").getall()
#         ptype_contest = response.css(".title .tag::text").getall()
#         banner = response.css(".d-banner")
#         stags = response.css(".tag-list .tag .highlight .text::text").getall()
#         data = dict(
#             has_banner=bool(banner),
#             # word_num, status, click_num, last_update
#             **self._row(row),
#             # praise_num, like_num
#             **self._btns(btns),
#             # ptype, contest
#             **self._ptype_contest(ptype_contest),
#             tags=stags,
#             # nid, cover, title, author, score, genre
#             **meta_info,
#         )
#         comment_data = self.get_comment(data["nid"])
#         yield Meta(**data, **comment_data)
#         # yield Request(
#         #     self._get_comment_url(data["nid"]),
#         #     callback=self.parse_comment,
#         #     cb_kwargs={"data": data},
#         # )
#
#     # def _get_comment_url(self, nid: int) -> str:
#     #     return urljoin(self._common_url, f"?{urlencode(params)}")
#
#     def get_comment(self, nid: int) -> dict[str, int]:
#         ua = self.settings.get("USER_AGENT", "")
#         headers = {"User-Agent": ua}
#         params = {"op": "getcomment", "nid": nid, "_": int(time() * 1000)}
#         try:
#             res = self.session.get(
#                 self._common_url, params=params, headers=headers, timeout=10
#             )
#             res.raise_for_status()
#             data = res.json()
#         except requests.HTTPError:
#             data = {}
#         return dict(
#             comment_num=data.get("ShortCommentNum"),
#             review_num=data.get("LongCommentNum"),
#         )
#
#     def _join_url(self):
#         params = {"PageIndex": self.curr_page}
#         return urljoin(self._base_url, f"?{urlencode(params)}")
#
#     def parse(self, response: HtmlResponse):
#         items = response.css(".Comic_Pic_List")
#         if not items:
#             raise CloseSpider("No items.")
#         for item in items:
#             novel_url: str | None = item.css(".Conjunction a::attr(href)").get()
#             cover: str | None = item.css(".Conjunction a img::attr(src)").get()
#             title: str | None = item.css(".Conjunction a img::attr(alt)").get()
#             author: str | None = item.css('a[id*="AuthorLink"]::text').get()
#             score: str | None = item.css(".font_red::text").get()
#             genre: str | None = item.css(".font_red ~a::text").get()
#             meta_info = dict(
#                 nid=int(novel_url.strip("/").split("/")[-1] if novel_url else 0),
#                 title=(title.strip() if title else ""),
#                 author=(author.strip() if author else ""),
#                 score=float(score.strip().replace("分", "") if score else 5),
#                 genre=(genre.strip() if genre else ""),
#                 cover=cover,
#             )
#             if novel_url:
#                 yield response.follow(
#                     novel_url,
#                     callback=self.parse_detail,
#                     cb_kwargs={"meta_info": meta_info},
#                 )
#         self.curr_page += 1
#         if self.curr_page <= self.end_page:
#             yield response.follow(self._join_url(), callback=self.parse)
#
#     def _row(self, row: list[str]) -> dict[str, int | str | datetime]:
#         # ['类型：魔幻', '字数：3240533字[连载中]', '点击：4757.4万', '更新：2026/5/25 20:26:36']
#         values = [item.split("：")[-1] for item in row]
#         _, wordnum_status, click_num, last_update = values
#         word_num, status = wordnum_status.split("字[")
#         status = status.replace("]", "")
#         return dict(
#             word_num=int(word_num),
#             status=status,
#             click_num=int(
#                 click_num
#                 if "万" not in click_num
#                 else float(click_num.replace("万", "")) * 10_000
#             ),
#             last_update=datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S"),
#         )
#
#     def _btns(self, btns: list[str]) -> dict[str, int]:
#         # ['点击阅读', '赞 27872', '收藏 278629']
#         # ['赞 294', '收藏 3066']
#         praise_num, like_num = [int(btn.split(" ")[-1]) for btn in btns[-2:]]
#         return dict(
#             praise_num=praise_num,
#             like_num=like_num,
#         )
#
#     def _ptype_contest(self, ptype_contest: list[str]) -> dict[str, str]:
#         # ['VIP', '第九届冬季征文']
#         # ['签约', '2026春季征文']
#         # ['征文大赛长篇']
#         # ['VIP']
#         # []
#         ptypes: set[str] = {"签约", "VIP"}
#         ptype_contest: set[str] = set(ptype_contest)
#         ptype = ptypes & ptype_contest
#         contest = ptype_contest - ptypes
#         return dict(
#             ptype=("免费" if not ptype else ptype.pop()),
#             contest=("" if not contest else contest.pop()),
#         )
