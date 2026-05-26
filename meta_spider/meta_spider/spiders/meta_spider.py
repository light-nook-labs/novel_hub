import scrapy
from scrapy import spiders

from meta_spider import utils


class MetaSpider(spiders.Spider):
    """PC Website"""
    name = 'meta_spider'

    async def start(self):
        url = 'https://book.sfacg.com/List/default.aspx?PageIndex='
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=12419',
        self.begin_num = int(getattr(self, "begin", '1'))
        self.num = int(getattr(self, "num", '2'))
        if self.begin_num is not None:
            url = f'{url}{self.begin_num}'
        yield scrapy.Request(url, self.parse)

    
    def parse(self, response):
        """Parse list page to acquire detail links."""
        detail_anchors = response.css('.Conjunction a')
        yield from response.follow_all(detail_anchors, callback=self.parse_detail)
        
        # Next page
        if response.css('.Conjunction a::attr(href)'):
            url, page_index = response.url.split('=')
            page_index = int(page_index) + 1

            # Stop
            if page_index - self.begin_num > self.num:
                return

            next_page = f'{url}={page_index}'
            yield response.follow(next_page, callback=self.parse)

