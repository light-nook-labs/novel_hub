from enum import IntEnum


class Genre(IntEnum):
    """小说分类枚举。

    中文标签 -> Genre.from_label()，整数值存入数据库。
    """

    MAGIC = 1  # 魔幻
    FANTASY = 2  # 玄幻
    ANCIENT = 3  # 古风
    SF = 4  # 科幻
    SCHOOL = 5  # 校园
    URBAN = 6  # 都市
    GAME = 7  # 游戏
    DOUJIN = 8  # 同人
    MYSTERY = 9  # 悬疑
    ADVENTURE = 98  # 冒险类
    OTHER = 99  # 其他

    @property
    def label(self) -> str:
        """中文标签，如 Genre.MAGIC.label -> '魔幻'"""
        return _GENRE_TO_LABEL[self]

    @classmethod
    def from_label(cls, label: str) -> "Genre":
        """从中文标签反查枚举，未匹配时返回 OTHER"""
        return _LABEL_TO_GENRE.get(label, cls.OTHER)

    @property
    def en_name(self) -> str:
        """英文名称，如 Genre.MAGIC.en_name -> 'Magic'"""
        return self.name.title()


# alias
Catalogy = Genre


class Status(IntEnum):
    """小说连载状态枚举。

    中文标签 -> Status.from_label()，整数值存入数据库。
    """

    FINISHED = 1  # 已完结
    ON_GOING = 2  # 连载中
    ACTIVE = 2  # 连载中（别名，与 ON_GOING 同值）
    DIED = 3  # 断更
    ACTIVE_F = 4  # 完结但读者活跃
    ACTIVE_D = 5  # 断更但读者活跃
    OTHER = 99  # 其他

    @property
    def label(self) -> str:
        """中文标签，如 Status.FINISHED.label -> '已完结'"""
        return _STATUS_TO_LABEL[self]

    @classmethod
    def from_label(cls, label: str) -> "Status":
        """从中文标签反查枚举，未匹配时返回 OTHER"""
        return _LABEL_TO_STATUS.get(label, cls.OTHER)

    @property
    def en_name(self) -> str:
        """英文名称，如 Status.FINISHED.en_name -> 'Finished'"""
        return self.name.title()


class PType(IntEnum):
    """小说付费类型枚举。

    中文标签 -> PType.from_label()，整数值存入数据库。
    """

    FREE = 1  # 免费
    SIGN = 2  # 签约
    VIP = 3  # VIP
    OTHER = 99  # 其他

    @property
    def label(self) -> str:
        """中文标签，如 PType.FREE.label -> '免费'"""
        return _PTYPE_TO_LABEL[self]

    @classmethod
    def from_label(cls, label: str) -> "PType":
        """从中文标签反查枚举，未匹配时返回 OTHER"""
        return _LABEL_TO_PTYPE.get(label, cls.OTHER)

    @property
    def en_name(self) -> str:
        """英文名称，如 PType.FREE.en_name -> 'Free'"""
        return self.name.title()


######################
# Bidirectional Maps #
######################

_GENRE_TO_LABEL = {
    Genre.MAGIC: "魔幻",
    Genre.FANTASY: "玄幻",
    Genre.ANCIENT: "古风",
    Genre.SF: "科幻",
    Genre.SCHOOL: "校园",
    Genre.URBAN: "都市",
    Genre.GAME: "游戏",
    Genre.DOUJIN: "同人",
    Genre.MYSTERY: "悬疑",
    Genre.ADVENTURE: "冒险类",
    Genre.OTHER: "其他",
}

_LABEL_TO_GENRE = {v: k for k, v in _GENRE_TO_LABEL.items()}

_STATUS_TO_LABEL = {
    Status.FINISHED: "已完结",
    Status.ON_GOING: "连载中",
    Status.DIED: "断更",
    Status.ACTIVE_F: "完结但读者活跃",
    Status.ACTIVE_D: "断更但读者活跃",
    Status.OTHER: "其他",
}

_LABEL_TO_STATUS = {v: k for k, v in _STATUS_TO_LABEL.items()}

_PTYPE_TO_LABEL = {
    PType.FREE: "免费",
    PType.SIGN: "签约",
    PType.VIP: "VIP",
    PType.OTHER: "其他",
}

_LABEL_TO_PTYPE = {v: k for k, v in _PTYPE_TO_LABEL.items()}
