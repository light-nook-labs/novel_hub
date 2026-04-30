from meta_spider.utils.novel import pc2m_detail

pc_detail = 'https://book.sfacg.com/Novel/770214/'
m_detail = 'https://m.sfacg.com/b/770214/'

def test_pc2m_detail():
    assert pc2m_detail(pc_detail) == m_detail
    