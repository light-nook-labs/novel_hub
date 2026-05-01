from meta_spider.utils.novel import pc2m_detail, get_novel_id
from meta_spider.utils.field_parser import row_parser, btns_parser, title_tags_parser


pc_detail = 'https://book.sfacg.com/Novel/770214/'
m_detail = 'https://m.sfacg.com/b/770214/'

def test_pc2m_detail():
    assert pc2m_detail(pc_detail) == m_detail


def test_get_novel_id_pc():
    assert get_novel_id(pc_detail) == 770214


def test_get_novel_id_m():
    assert get_novel_id(m_detail) == 770214


def test_row_parser_case1():
    case1 = ['类型：都市', '字数：237905字[连载中]', '点击：203167', '更新：2026/4/30 16:11:48']
    assert row_parser(case1) == {
        "genre": "都市",
        "word_num": 237905,
        "status_id": 1,
        "click_num": 203167,
        "last_update": "2026-04-30 16:11:48"
    }


def test_row_parser_case2_finished():
    case2 = ['类型：玄幻', '字数：1000000字[已完结]', '点击：999999', '更新：2025/1/1 00:00:00']
    assert row_parser(case2) == {
        "genre": "玄幻",
        "word_num": 1000000,
        "status_id": 0,
        "click_num": 999999,
        "last_update": "2025-01-01 00:00:00"
    }


def test_row_parser_case3_died():
    case3 = ['类型：校园', '字数：50000字[连载中]', '点击：12345', '更新：2024/1/1 00:00:00']
    print(row_parser(case3))
    assert row_parser(case3) == {
        "genre": "校园",
        "word_num": 50000,
        "status_id": 2,
        "click_num": 12345,
        "last_update": "2024-01-01 00:00:00"
    }


def test_btns_parser_case1():
    case1 = ['点击阅读', '赞 294', '收藏 3066']
    assert btns_parser(case1) == {
        'praise_num': 294,
        'like_num': 3066,
    }


def test_btns_parser_case2():
    case2 = ['赞 294', '收藏 3066']
    assert btns_parser(case2) == {
        'praise_num': 294,
        'like_num': 3066,
        'status_id': 3,
    }


def test_title_tags_parser_case1():
    case1 = ['VIP', '第九届冬季征文']  
    print(title_tags_parser(case1))   
    assert title_tags_parser(case1) == {
        'price_type_id': 2,
        'contest': '第九届冬季征文',
    }


def test_title_tags_parser_case2():
    case2 = ['第九届冬季征文']     
    assert title_tags_parser(case2) == {
        'price_type_id': 0,
        'contest': '第九届冬季征文',
    }


def test_title_tags_parser_case3():
    case3 = ['VIP']     
    assert title_tags_parser(case3) == {
        'price_type_id': 2,
        'contest': '',
    }


def test_title_tags_parser_case4():
    case4 = []     
    assert title_tags_parser(case4) == {
        'price_type_id': 0,
        'contest': '',
    }