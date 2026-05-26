from urllib.parse import urlencode, urljoin
from typing import Any
import re
from datetime import datetime

from scrapy import Spider, Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse


class MetaSpider(Spider):
    # scrapy shell "https://book.sfacg.com/List/default.aspx?PageIndex=1"
    name = "meta"
    allowed_domains = ["book.sfacg.com"]
    # start_urls = ["https://book.sfacg.com"]
    _base_url = "https://book.sfacg.com/List/default.aspx"
    _params = {
        "PageIndex": 0,
    }

    async def start(self):
        urls = [self._join_url()]
        print(urls)
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response: HtmlResponse):
        items = response.css(".Comic_Pic_List")
        if not items:
            raise CloseSpider("No items.")
        for item in items:
            novel_url: str | None = item.css(
                ".Conjunction a::attr(href)"
            ).get()
            cover: str | None = item.css(".Conjunction a img::attr(src)").get()
            title: str | None = item.css(".Conjunction a img::attr(alt)").get()
            author: str | None = item.css('a[id*="AuthorLink"]::text').get()
            score: str | None = item.css(".font_red::text").get()
            genre: str | None = item.css(".font_red ~a::text").get()
            meta_info = dict(
                nid=int(
                    novel_url.strip("/").split("/")[-1] if novel_url else 0
                ),
                cover=cover,
                title=(title.strip() if title else ""),
                author=(author.strip() if author else ""),
                score=float(score.strip().replace("分", "") if score else 5),
                genre=(genre.strip() if genre else ""),
            )
            if novel_url:
                yield response.follow(
                    novel_url,
                    callback=self.parse_detail,
                    cb_kwargs={"meta_info": meta_info},
                )
        yield response.follow(self._join_url(), callback=self.parse)

    def _row(self, row: list[str]) -> dict[str, int | str | datetime]:
        # ['类型：魔幻', '字数：3240533字[连载中]', '点击：4757.4万', '更新：2026/5/25 20:26:36']
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
                else int(click_num.replace("万")) * 10_000
            ),
            last_update=datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S"),
        )

    def _btns(self, btns: list[str]) -> dict[str, int]:
        # ['点击阅读', '赞 27872', '收藏 278629']
        # ['赞 294', '收藏 3066']
        praise_num, like_num = [int(btn.split(" ")[-1]) for btn in btns[-2:]]
        data = dict(
            praise_num=praise_num,
            like_num=like_num,
        )
        return data

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
            price_type=("免费" if not ptype else ptype.pop()),
            contest=("" if not contest else contest.pop()),
        )

    def parse_detail(self, response: HtmlResponse, meta_info: dict[str, Any]):
        row = response.css(".count-detail .text-row .text::text").getall()

        btns = response.css("#BasicOperation .btn::text").getall()
        # ['点击阅读', '赞 27872', '收藏 278629']

        ptype_contest = response.css(".title .tag::text").getall()
        # ['VIP', '十一征长篇']

        banner = response.css(".d-banner")

        stags = response.css(".tag-list .tag .highlight .text::text").getall()
        yield dict(
            # nid, cover, title, author, score, genre
            **meta_info,
            has_banner=bool(banner),
            **self._row(row),
            **self._btns(btns),
            **self._ptype_contest(ptype_contest),
            tags=stags,
        )

    def _join_url(self):
        self._params["PageIndex"] += 1
        if self._params["PageIndex"] > 3:
            raise CloseSpider()
        params = urlencode(self._params)
        return urljoin(self._base_url, f"?{params}")
