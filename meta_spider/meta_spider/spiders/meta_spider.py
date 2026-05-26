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


#     def parse_detail(self, response):
#         """Parse meta data from PC detail page."""
#         row = utils.get_clean_all(response, '.count-detail .text-row .text')
#         btns = utils.get_clean_all(response, '#BasicOperation .btn')
#         title_tags = utils.get_clean_all(response, '.title .tag')    
#         # Cannot use dict(), it doesn't allow the same key appear more than once
#         banner = utils.get_banner(response)
#         yield {
#             "nid": utils.get_novel_id(response.url),
#             "novel_title": utils.get_clean(response, '.title .text'),
#             "author": utils.get_clean(response, '.author-name > span'),
#             **utils.title_tags_parser(title_tags),

#             # Cannot change order, 2nd status_id will cover the first one
#             **utils.row_parser(row),
#             **utils.btns_parser(btns),

#             # "cover": utils.get_attribute(response, '.summary-pic img'),
#             "cover": utils.get_attribute(response, '.article-list .figure .pic .block-img'),
#             'banner': banner,
#             # ['恋爱', '纯爱', '日常', '女性主角', '变身']
#             # It will be used to create another table
#             'tags': utils.get_clean_all(response, '.tag-list .tag .highlight .text')
#         }
