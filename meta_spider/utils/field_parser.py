import re
from datetime import datetime, timedelta

from .constants import STATUS_LIST, PRICE_TYPES


pattern = re.compile(r'(\d+)字\[(.+)\]')


def _row_parser(data: str, last_update: str) -> dict[str, int|str]:
    """Extract data from 237905字[连载中]
    STATUS_LIST = ['已完结', '连载中', '断更']
    + 0: fin
    + 1: on-going
    + 2: died, more than 30d without updating
    """
    word_num, status = pattern.search(data).groups()
    status_id = STATUS_LIST.index(status)
    d = datetime.strptime(last_update, "%Y/%m/%d %H:%M:%S")
    if status_id:
        now = datetime.now()
        if now - d > timedelta(days=30):
            status_id = 2
    return dict(
        word_num=int(word_num), 
        status_id=status_id, 
        last_update=d.strftime("%Y-%m-%d %H:%M:%S")
    )


def row_parser(row: list[str]) -> dict[str, str|int]:
    """Parse structure data from row. We can always extract 5 items form a row:
    * genre
    * word_num
    * status 
        + 0: fin
        + 1: on-going
        + 2: died, more than 1 month without updating
        + 3: deleted, the book was deleted but can visit its detail page
    * click_num
    * last_update
    >>> row=get_clean_all(response, '.count-detail .text-row .text'),
    >>> ['类型：都市', '字数：237905字[连载中]', '点击：203167', '更新：2026/4/30 16:11:48']
    """
    genre, data, click_num, last_update = [item.split('：')[-1] for item in row]
    return dict(
        genre=genre,
        click_num=int(click_num),
        **_row_parser(data, last_update),
    )


def btns_parser(btns: list[str]) -> dict[str, int]:
    """Extract data from btns.
    >>> btns=get_clean_all(response, '#BasicOperation .btn'),
    >>> ['点击阅读', '赞 294', '收藏 3066']
    >>> ['赞 294', '收藏 3066']
    """
    length = len(btns)
    praise_num, like_num = [int(btn.split(' ')[-1]) for btn in btns[-2:]]
    data = dict(
        praise_num=praise_num,
        like_num=like_num,
    )
    if length == 2:
        data['status_id'] = 3
    return data


def title_tags_parser(title_tags: list[str]) -> dict[str, str|int]:
    """Extract data from title_tags. PRICE_TYPES = ['免费', '签约', 'VIP']
    >>> title_tags=get_clean_all(response, '.title .tag'),
    >>> ['VIP', '第九届冬季征文']        
    >>> ['签约', '2026春季征文']        
    >>> ['征文大赛长篇'] 
    >>> ['VIP'] 
    >>> []        
    """
    price_type_id = 0
    contest = ''
    length = len(title_tags)
    if length:
        # Assume index 0 is price_type
        price_type = title_tags[0]
        try:
            price_type_id = PRICE_TYPES.index(price_type)
        except ValueError:
            price_type_id = 0
            contest = price_type
        if length >= 2:
            contest = title_tags[-1]
    return dict(
        price_type_id=price_type_id,
        contest=contest,
    )


