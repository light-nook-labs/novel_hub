from scrapy import spiders

from meta_spider.utils import get_clean, get_clean_all, get_attribute


class MetaSpider(spiders.Spider):
    """PC Website"""
    name = 'meta_spider'
    start_urls = [
        # 'https://book.sfacg.com/List/'
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=1'
        # 'https://book.sfacg.com/List/default.aspx?PageIndex=12420'
        'https://book.sfacg.com/List/default.aspx?PageIndex=12418'
    ]

    
    def parse(self, response):
        detail_anchors = response.css('.Conjunction a')
        yield from response.follow_all(detail_anchors, callback=self.parse_detail)
        
        # Next page
        if response.css('.Conjunction a::attr(href)'):
            url, page_index = response.url.split('=')
            page_index = int(page_index) + 1
            next_page = f'{url}={page_index}'
            yield response.follow(next_page, callback=self.parse)


    def parse_detail(self, response):
        
        yield dict(
            novel_id=int(response.url.split('/')[-2]),
            novel_title=get_clean(response, '.title .text'),
            # ['VIP', '第九届冬季征文']
            title_tags=get_clean_all(response, '.title .tag'),
            cover=get_attribute('.summary-pic img'),
            author=get_clean(response, '.author-name > span'),
            # ['类型：都市', '字数：237905字[连载中]', '点击：203167', '更新：2026/4/30 16:11:48']
            row=get_clean_all(response, '.count-detail .text-row .text'),
            btns=get_clean_all(response, '#BasicOperation .btn'),
            # ['恋爱', '纯爱', '日常', '女性主角', '变身']
            tags=get_clean_all(response, '.tag-list .tag .highlight .text'),
            # ticket_num=get_clean(response, '.votes-row .text span'),
            # comment_num=get_clean(response, '#CommentNum .nav-item')
        )

"""
ticket_num POST 
https://book.sfacg.com/ajax/ashx/Common.ashx?op=ticketinfo
# 1. 参数
params = {
    "op": "ticketinfo"
}

# 2. 表单数据（Form Data）
data = {
    "nid": "770214"
}


# comments
https://book.sfacg.com/ajax/ashx/Common.ashx?op=getcomment&nid=770214&_=1777541692123

params = {
    op getcomment
    nid 770214
    _ 1777541692123
    }
"""

"""
>>> response.css('#typeMenu a::text').getall()
['魔幻', '玄幻', '古风', '科幻', '校园', '都市', '游戏', '同人', '悬疑']

>>> response.css('.Conjunction a::attr(href)').getall()
['/Novel/758439/', '/Novel/774264/', '/Novel/774528/', '/Novel/763381/', '/Novel/771432/', '/Novel/774148/', '/Novel/755866/', '/Novel/773905/', '/Novel/763208/', '/Novel/768157/', '/Novel/767896/', '/Novel/771840/', '/Novel/765742/', '/Novel/767435/', '/Novel/385603/', '/Novel/770530/', '/Novel/774086/', '/Novel/771794/', '/Novel/774609/', '/Novel/766504/']
"""

