from .meta_spider import MetaSpider
from meta_spider.utils import pc2m_detail, get_clean, get_clean_all, get_attribute, get_novel_id


class MMetaSpider(MetaSpider):
    """MobiLe Website, change PC detail link to mobile page to crawl meta data."""
    name = 'mmeta_spider'
    
    def parse_detail(self, response):
        """Switch pc detail url to mobile url and parse detail page."""
        mobile_url = pc2m_detail(response.url)
        yield response.follow(mobile_url, callback=self.parse_detail_m)

    def parse_detail_m(self, response):
        """Parse mobile detail page."""
        yield dict(
            novel_id=get_novel_id(response.url),
            novel_title=get_clean(response, '.book_newtitle'),
            cover=get_attribute(response, '.book_info li img'),
            like_num=get_clean(response, '.icon-heart2 ~ small'),
            praise_num=get_clean(response, '.icon-thumbs-up ~ small'),
            ticket_num=get_clean(response, '.icon-tag ~ small'),
            comment_num=get_clean(response, '.book_pinglun_more'),

            # ['魔幻', '连载中', 'VIP']
            title_tags=get_clean_all(response, '.book_info2 span'),

            # 第九届冬季征文
            label=get_clean(response, '.book_info2 label'),

            # ['莫留十三月 / 486231字  / 507721', '26-04-30 21:02']
            info=get_clean_all(response, '.book_info3'),


            # ['类型：都市', '字数：237905字[连载中]', '点击：203167', '更新：2026/4/30 16:11:48']
            row=get_clean_all(response, '.count-detail .text-row .text'),
            btns=get_clean_all(response, '#BasicOperation .btn'),

            # ['恋爱', '纯爱', '日常', '女性主角', '变身']
            tags=get_clean_all(response, '.tag-list .tag .highlight .text'),
            # ticket_num=get_clean(response, '.votes-row .text span'),
            # comment_num=get_clean(response, '#CommentNum .nav-item')
        )


"""
comment GET 
https://m.sfacg.com/API/HTML5.ashx?op=getcomment&nid=765778&_=1777549787135

op
getcomment
nid
765778
_
1777549787135
"""