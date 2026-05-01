import re
from datetime import datetime

from .constants import STATUS_LIST


pattern = re.compile(r'(\d+)字[(.+)]')


def get_status_id(status: str) -> int:
    """STATUS_LIST = ['已完结', '连载中', '断更']
    + 0: fin
    + 1: on-going
    + 2: died, more than 1 month without updating
    """
    status_id = STATUS_LIST.index(status)
    if status_id:
        pass
    return status_id


def row_parser(row: list[str]) -> dict[str, str|int]:
    """Parse structure data from row. We can always extract 5 items form a row:
    * genre
    * word_num
    * status 
        + 0: fin
        + 1: on-going
        + 2: died, more than 1 month without updating
    * click_num
    * last_update
    >>> row=get_clean_all(response, '.count-detail .text-row .text'),
    >>> ['类型：都市', '字数：237905字[连载中]', '点击：203167', '更新：2026/4/30 16:11:48']
    """
    genre, data, click_num, last_update = [item.split('：')[-1] for item in row]
    word_num, status = pattern.search(data).groups()
    return dict(
        genre=genre,
        word_num=word_num,
        status=status,
        click_num=click_num,
        last_update=last_update,
    ) # unfinished


