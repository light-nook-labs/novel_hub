from datetime import datetime
from time import time
from typing import Any
from urllib.parse import urlencode, urljoin

from scrapy import Spider, Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse

from models import Meta


class MetaBatchSpider(Spider):
    name = "meta_batch"
    allowed_domains = ["book.sfacg.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from scrapy.utils.project import get_project_settings

        settings = get_project_settings()
        toml = settings.get("TOML", {})
        scraper = toml.get("scraper", {})
        self._base_url = "https://book.sfacg.com/List/default.aspx"
        self._common_url = scraper.get(
            "common_url", "https://book.sfacg.com/ajax/ashx/Common.ashx"
        )

    async def start(self):
        """CLI Args

        Args:
            begin: start page
            num: total num

        Examples:
            - scrapy crawl meta_batch -o o.jsonl -a num=3
            - scrapy crawl meta_batch -o o.jsonl -a num=3 -a begin=22
            - scrapy crawl meta_batch -o o.jsonl -a begin=12465
        """
        self.begin_num = int(getattr(self, "begin", 1))
        self.curr_page = self.begin_num
        self.total_num = int(getattr(self, "num", 2))
        self.end_page = self.begin_num + self.total_num - 1

        yield Request(self._join_url(), callback=self.parse)

    def parse(self, response: HtmlResponse):
        items = response.css(".Comic_Pic_List")
        if not items:
            raise CloseSpider("No items.")
        for item in items:
            novel_url: str | None = item.css(".Conjunction a::attr(href)").get()
            cover: str | None = item.css(".Conjunction a img::attr(src)").get()
            title: str | None = item.css(".Conjunction a img::attr(alt)").get()
            author: str | None = item.css('a[id*="AuthorLink"]::text').get()
            genre: str | None = item.css(".font_red ~a::text").get()
            meta_info = dict(
                nid=int(novel_url.strip("/").split("/")[-1] if novel_url else 0),
                title=(title.strip() if title else ""),
                author=(author.strip() if author else ""),
                genre=(genre.strip() if genre else ""),
                cover=cover,
            )
            if novel_url:
                yield response.follow(
                    novel_url,
                    callback=self.parse_detail,
                    cb_kwargs={"meta_info": meta_info},
                )
        self.curr_page += 1
        if self.curr_page <= self.end_page:
            yield response.follow(self._join_url(), callback=self.parse)

    def parse_detail(self, response: HtmlResponse, meta_info: dict[str, Any]):
        row = response.css(".count-detail .text-row .text::text").getall()
        btns = response.css("#BasicOperation .btn::text").getall()
        ptype_contest = response.css(".title .tag::text").getall()
        banner = response.css(".d-banner")
        stags = response.css(".tag-list .tag .highlight .text::text").getall()
        data = dict(
            has_banner=bool(banner),
            # word_num, status, click_num, last_update
            **self._row(row),
            # praise_num, like_num
            **self._btns(btns),
            # ptype, contest
            **self._ptype_contest(ptype_contest),
            tags=stags,
            # nid, cover, title, author, genre
            **meta_info,
        )
        comment_url = self._get_comment_url(data["nid"])
        yield Request(
            comment_url,
            callback=self.parse_comment,
            cb_kwargs={"data": data},
        )

    def parse_comment(self, response, data: dict[str, Any]):
        comment_data = response.json()
        yield Meta(
            **data,
            comment_num=comment_data.get("ShortCommentNum"),
            review_num=comment_data.get("LongCommentNum"),
        )

    def _get_comment_url(self, nid: int) -> str:
        params = {
            "op": "getcomment",
            "nid": nid,
            "_": int(time() * 1000),
        }
        return urljoin(self._common_url, f"?{urlencode(params)}")

    def _join_url(self):
        params = {"PageIndex": self.curr_page}
        return urljoin(self._base_url, f"?{urlencode(params)}")

    def _row(self, row: list[str]) -> dict[str, int | str | datetime]:
        # ['类型：魔幻', '字数：3240533字[连载中]',
        #  '点击：4757.4万', '更新：2026/5/25 20:26:36']
        values = [item.split("：")[-1] for item in row]
        _, wordnum_status, click_num, last_update = values
        word_num, status = wordnum_status.split("字[")
        status = status.replace("]", "")
        return dict(
            word_num=int(word_num),
            status=status,
            click_num=int(
                click_num
                if "万" not in click_num
                else float(click_num.replace("万", "")) * 10_000
            ),
            last_update=datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S"),
        )

    def _btns(self, btns: list[str]) -> dict[str, int]:
        # ['点击阅读', '赞 27872', '收藏 278629']
        # ['赞 294', '收藏 3066']
        praise_num, like_num = [int(btn.split(" ")[-1]) for btn in btns[-2:]]
        return dict(
            praise_num=praise_num,
            like_num=like_num,
        )

    def _ptype_contest(self, ptype_contest: list[str]) -> dict[str, str]:
        # ['VIP', '第九届冬季征文']
        # ['签约', '2026春季征文']
        # ['征文大赛长篇']
        # ['VIP']
        # []
        ptypes: set[str] = {"签约", "VIP"}
        ptype_contest: set[str] = set(ptype_contest)
        ptype = ptypes & ptype_contest
        contest = ptype_contest - ptypes
        return dict(
            ptype=("免费" if not ptype else ptype.pop()),
            contest=("" if not contest else contest.pop()),
        )
