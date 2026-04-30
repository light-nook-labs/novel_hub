from meta_spider.utils.novel import pc2m_detail, get_novel_id

pc_detail = 'https://book.sfacg.com/Novel/770214/'
m_detail = 'https://m.sfacg.com/b/770214/'

def test_pc2m_detail():
    assert pc2m_detail(pc_detail) == m_detail


def test_get_novel_id_pc():
    assert get_novel_id(pc_detail) == 770214


def test_get_novel_id_m():
    assert get_novel_id(m_detail) == 770214