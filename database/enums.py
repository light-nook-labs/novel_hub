"""
Enums and mappers
"""


from enum import IntEnum


class LabeledIntEnum(IntEnum):
    """带中文标签的 IntEnum 基类。

    子类只需定义成员和 _labels 映射，自动获得 label / en_name / from_label。
    """

    @property
    def label(self) -> str:
        """中文标签，如 Genre.MAGIC.label -> '魔幻'"""
        return self._mapping[self]

    @property
    def en_name(self) -> str:
        """英文名称，如 Genre.MAGIC.en_name -> 'Magic'"""
        return self.name.title()

    @classmethod
    def from_label(cls, label: str) -> "LabeledIntEnum":
        """从中文标签反查枚举，未匹配时返回 OTHER"""
        reverse = {v: k for k, v in cls._mapping.items()}
        return reverse.get(label, cls.OTHER)


class Genre(LabeledIntEnum):
    """小说分类枚举。"""

    MAGIC = 1
    FANTASY = 2
    ANCIENT = 3
    SF = 4
    SCHOOL = 5
    URBAN = 6
    GAME = 7
    DOUJIN = 8
    MYSTERY = 9

    # Abnormal genre, maybe bugs of the website we crawled
    LOVE = 97
    ADVENTURE = 98

    # Fallback
    OTHER = 99


Genre._mapping = {
    Genre.MAGIC: "魔幻",
    Genre.FANTASY: "玄幻",
    Genre.ANCIENT: "古风",
    Genre.SF: "科幻",
    Genre.SCHOOL: "校园",
    Genre.URBAN: "都市",
    Genre.GAME: "游戏",
    Genre.DOUJIN: "同人",
    Genre.MYSTERY: "悬疑",
    Genre.LOVE: "爱情类",
    Genre.ADVENTURE: "冒险类",
    Genre.OTHER: "其他",
}



class Status(LabeledIntEnum):
    """小说连载状态枚举。"""

    FINISHED = 1
    ON_GOING = 2
    DIED = 3
    ACTIVE_F = 4
    ACTIVE_D = 5
    OTHER = 99


Status._mapping = {
    Status.FINISHED: "已完结",
    Status.ON_GOING: "连载中",
    Status.DIED: "断更",
    Status.ACTIVE_F: "完结但读者活跃",
    Status.ACTIVE_D: "断更但读者活跃",
    Status.OTHER: "其他",
}


class PType(LabeledIntEnum):
    """小说付费类型枚举。"""

    FREE = 1
    SIGN = 2
    VIP = 3
    OTHER = 99


PType._mapping = {
    PType.FREE: "免费",
    PType.SIGN: "签约",
    PType.VIP: "VIP",
    PType.OTHER: "其他",
}
