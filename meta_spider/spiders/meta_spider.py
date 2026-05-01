from scrapy import spiders

from meta_spider import utils


class MetaSpider(spiders.Spider):
    """PC Website"""
    name = 'meta_spider'
    start_urls = [
        # 'https://book.sfacg.com/List/'
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=1'
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=12420'
        'https://book.sfacg.com/List/default.aspx?PageIndex=12418'
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=12419',
    ]

    
    def parse(self, response):
        """Parse list page to acquire detail links."""
        detail_anchors = response.css('.Conjunction a')
        yield from response.follow_all(detail_anchors, callback=self.parse_detail)
        
        # Next page
        if response.css('.Conjunction a::attr(href)'):
            url, page_index = response.url.split('=')
            page_index = int(page_index) + 1
            next_page = f'{url}={page_index}'
            yield response.follow(next_page, callback=self.parse)


    def parse_detail(self, response):
        """Parse meta data from PC detail page."""

        # ['恋爱', '纯爱', '日常', '女性主角', '变身']
        # It will be used to create another table
        # tags = utils.get_clean_all(response, '.tag-list .tag .highlight .text')

        row = utils.get_clean_all(response, '.count-detail .text-row .text')
        btns = utils.get_clean_all(response, '#BasicOperation .btn')
        title_tags = utils.get_clean_all(response, '.title .tag')    
        # Cannot use dict(), it doesn't allow the same key appear more than once   
        yield {
            "novel_id": utils.get_novel_id(response.url),
            "novel_title": utils.get_clean(response, '.title .text'),
            "author": utils.get_clean(response, '.author-name > span'),
            **utils.title_tags_parser(title_tags),

            # Cannot change order, 2nd status_id will cover the first one
            **utils.row_parser(row),
            **utils.btns_parser(btns),

            "cover": utils.get_attribute(response, '.summary-pic img'),
        }
