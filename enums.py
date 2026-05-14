from enum import Enum


# GENRES = ['魔幻', '玄幻', '古风', '科幻', '校园', '都市', '游戏', '同人', '悬疑']
class Genre(Enum):
    MAGIC = 1  # 魔幻
    FANTASY = 2  # 玄幻
    ANCIENT = 3  # 古风
    SF = 4  # 科幻
    SCHOOL = 5  # 校园
    URBAN = 6  # 都市
    GAME = 7  # 游戏
    DOUJIN = 8  # 同人
    MYSTERY = 9  # 悬疑

    OTHER = 99  # 其他


# alias
Catalogy = Genre


# STATUS_LIST = ['已完结', '连载中', '断更']
class Status(Enum):
    FINISHED = 1  # 已完结
    ON_GOING = 2  # 连载中
    ACTIVE = 2  # 连载中 别名
    DIED = 3  # 断更
    ACTIVE_F = 4  # 完结但读者活跃
    ACTIVE_D = 5  # 断更但读者活跃

    OTHER = 99  # 其他


# PRICE_TYPES = ['免费', '签约', 'VIP']
class PType(Enum):
    FREE = 1  # 免费
    SIGN = 2  # 签约
    VIP = 3  # VIP付费

    OTHER = 99
