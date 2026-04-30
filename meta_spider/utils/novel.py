import re

# from .constants import *
from .constants import *
# PC_NOVEL_DETAIL = 'https://book.sfacg.com/Novel/'
# # 'https://book.sfacg.com/Novel/770214/'

# MOBILE_NOVEL_DETAIL = 'https://m.sfacg.com/b/'
# # 'https://m.sfacg.com/b/765778/'

pc_pattern = re.compile(r'^https://book.sfacg.com/Novel/(\d+)/?')
m_pattern = re.compile(r'^https://m.sfacg.com/b/(\d+)/?')

def pc2m_detail(url):
    match = pc_pattern.search(url)
    if not match:
        raise ValueError('Invalid PC url.')
    else:
        book_id = match.group(1)
    return MOBILE_NOVEL_DETAIL + book_id + '/'


