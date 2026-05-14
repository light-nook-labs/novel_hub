# from datetime import datetime, timedelta
# import re
# from enums import Genre, Catalogy

# if __name__ == "__main__":
#     # date_str = '2026/4/30 16:11:48'
#     # now = datetime.now()
#     # d = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
#     # delta = timedelta(days=30)
#     # print(now, d, delta, sep='\n')
#     # print(now - d < delta)
#     # pattern = re.compile(r'(\d+)字\[(.+)\]')
#     # s = '50000字[连载中]'
#     # print(pattern.search(s).groups())
#     print(Genre(1))
#     print(Catalogy.MAGIC)


from datetime import datetime
from sqlmodel import Session, select
from models import Author, Novel, Banner, Tag, Contest, NovelTagLink
from enums import Genre, PType, Status
from db import engine, SQLModel  # 你已创建

SQLModel.metadata.create_all(engine)


# ======================
# 你的映射规则
# ======================
STATUS_LIST = ['已完结', '连载中', '断更']
PRICE_TYPES = ['免费', '签约', 'VIP']
GENRES = ['魔幻', '玄幻', '古风', '科幻', '校园', '都市', '游戏', '同人', '悬疑']

# ======================
# 你的原始数据
# ======================
data = {
    "nid": 716851,
    "novel_title": "崩坏！但是不只一只龙！",
    "author": "伊维尔卡纳",
    "price_type_id": 1,
    "contest": "",
    "genre": "游戏",
    "click_num": 60983,
    "word_num": 400750,
    "status_id": 2,
    "last_update": "2025-10-31 08:07:23",
    "praise_num": 256,
    "like_num": 459,
    "cover": "http://rs.sfacg.com/web/novel/images/NovelCover/Big/2026/02/b9879432-65fc-4de6-8f67-d01d7b7f61c4.jpg",
    "banner": "",
    "tags": ["战斗", "恋爱", "无敌", "龙"]
}

# ======================
# 核心：数字 → 中文 → 枚举（别名匹配）
# ======================

# 1. 状态：status_id → 中文 → 枚举
status_text = STATUS_LIST[data["status_id"]]  # 2 → 断更
status = Status[status_text].value  # 用别名找到枚举 → 存入数字

# 2. 价格：price_type_id → 中文 → 枚举
price_text = PRICE_TYPES[data["price_type_id"]]  # 1 → 签约
ptype = PType[price_text].value

# 3. 分类：直接中文 → 枚举
genre_text = data["genre"]  # 游戏
genre = Genre[genre_text].value

# ======================
# 开始插入 DB
# ======================
with Session(engine) as session:
    # 1. 作者
    author = session.exec(select(Author).where(Author.name == data["author"])).first()
    if not author:
        author = Author(name=data["author"])
        session.add(author)
        session.commit()
        session.refresh(author)

    # 2. 征文
    contest = None
    if data["contest"]:
        contest = session.exec(select(Contest).where(Contest.name == data["contest"])).first()
        if not contest:
            contest = Contest(name=data["contest"])
            session.add(contest)
            session.commit()
            session.refresh(contest)

    # 3. 小说（全部传枚举，DB 自动存 int）
    novel = Novel(
        id=data["nid"],
        title=data["novel_title"],
        ptype=ptype,        # 枚举 → DB 存数字
        genre=genre,        # 枚举 → DB 存数字
        status=status,      # 枚举 → DB 存数字
        click_num=data["click_num"],
        word_num=data["word_num"],
        praise_num=data["praise_num"],
        like_num=data["like_num"],
        cover=data["cover"],
        last_update=datetime.strptime(data["last_update"], "%Y-%m-%d %H:%M:%S"),
        author_id=author.id,
        contest_id=contest.id if contest else None,
    )
    session.add(novel)
    session.commit()
    session.refresh(novel)

    # 4. Banner
    if data["banner"]:
        banner = Banner(url=data["banner"], novel_id=novel.id)
        session.add(banner)
        session.commit()

    # 5. 标签
    for tag_name in data["tags"]:
        tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.commit()
            session.refresh(tag)
        
        link = NovelTagLink(novel_id=novel.id, tag_id=tag.id)
        session.add(link)

    session.commit()

print("✅ 插入成功！数据库存储的是【枚举数字】，使用了【中文别名】匹配")