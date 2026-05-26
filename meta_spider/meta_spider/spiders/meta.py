from urllib.parse import urlencode, urljoin
from typing import Any

from scrapy import Spider, Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse

from meta_spider import utils

class MetaSpider(Spider):
    # scrapy shell "https://book.sfacg.com/List/default.aspx?PageIndex=1"  
    name = "meta"
    allowed_domains = ["book.sfacg.com"]
    # start_urls = ["https://book.sfacg.com"]
    _base_url = "https://book.sfacg.com/List/default.aspx"
    _params = {
        'PageIndex': 0,
    }

    async def start(self):
        urls = [self._join_url()]
        print(urls)
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response: HtmlResponse):
        items = response.css('.Comic_Pic_List')
        if not items:
            raise CloseSpider('No items.')
        for item in items:
            novel_url: str | None = item.css('.Conjunction a::attr(href)').get()
            cover: str | None = item.css('.Conjunction a img::attr(src)').get()
            title: str | None = item.css('.Conjunction a img::attr(alt)').get()
            author: str | None  = item.css('a[id*="AuthorLink"]::text').get()
            score: str | None = item.css('.font_red::text').get()
            genre: str | None = item.css('.font_red ~a::text').get()
            meta_info = dict(
                nid=int(novel_url.strip('/').split('/')[-1] if novel_url else 0),
                cover=cover,
                title=(title.strip() if title else ''),
                author=(author.strip() if author else ''),
                score=float(score.strip().replace('分', '') if score else 5),
                genre=(genre.strip() if genre else ''),
            )
            if novel_url:
                yield response.follow(novel_url, callback=self.parse_detail, cb_kwargs={'meta_info': meta_info})
        yield response.follow(self._join_url(), callback=self.parse)

    def parse_detail(self, response: HtmlResponse, meta_info: dict[str, Any]):
        row = utils.get_clean_all(response, '.count-detail .text-row .text')
        btns = utils.get_clean_all(response, '#BasicOperation .btn')
        title_tags = utils.get_clean_all(response, '.title .tag')    
        # Cannot use dict(), it doesn't allow the same key appear more than once
        banner = utils.get_banner(response)
        yield {
            **meta_info,
            **utils.title_tags_parser(title_tags),

            # Cannot change order, 2nd status_id will cover the first one
            **utils.row_parser(row),
            **utils.btns_parser(btns),

            # "cover": utils.get_attribute(response, '.summary-pic img'),
            'has_banner': bool(banner),
            # ['恋爱', '纯爱', '日常', '女性主角', '变身']
            # It will be used to create another table
            'tags': utils.get_clean_all(response, '.tag-list .tag .highlight .text')
        }


    def _join_url(self):
        self._params["PageIndex"] += 1
        if self._params["PageIndex"] > 3:
            raise CloseSpider()
        params = urlencode(self._params)
        return urljoin(self._base_url, f"?{params}")




