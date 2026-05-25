"""Enums and mappings"""

from enum import IntEnum
from typing import Literal
import re

pattern = re.compile(r"^[-\w]+$", re.I)


class Mapping:
    """Maps English attribute names to Chinese labels.
    Case insensitive.
    'other' mapped to '其他' is reserved.
    """

    def __init__(self, **en_zh_mapping_dict):
        self._en_zh, self._zh_en = self._validate_and_create_mapping_dict(
            en_zh_mapping_dict
        )
        self._enum: IntEnum = IntEnum(
            f"{self.__class__.__name__}Enum",
            [k.upper() for k in self._en_zh.keys()],
        )

    def _validate_and_create_mapping_dict(
        self, en_zh_mapping_dict: dict
    ) -> tuple[dict[str, str], dict[str, str]]:
        en_zh: dict[str, str] = {}
        zh_en: dict[str, str] = {}
        invalid_keys = [
            k
            for k in en_zh_mapping_dict
            if not pattern.fullmatch(k) or k == "other"
        ]
        if invalid_keys:
            if "other" in invalid_keys:
                raise ValueError("'other' is reserved for fallback key.")
            raise ValueError(
                f"Invalid keys: {invalid_keys}. Keys must consist of ascii letters, digits, '_' or '-'."
            )
        zh_set: set[str] = set(en_zh_mapping_dict.values())
        if len(zh_set) != len(en_zh_mapping_dict):
            raise ValueError(
                "Keys and Values must be unique in en_zh_mapping_dict."
            )
        if "其他" in zh_set:
            raise ValueError("'其他' is reversed for fallback value.")
        mapping = dict(other="其他")
        mapping.update(en_zh_mapping_dict)
        for en, zh in mapping.items():
            en = en.lower()
            en_zh[en] = zh
            zh_en[zh] = en
        return en_zh, zh_en

    @property
    def enum(self) -> IntEnum:
        """Get enum. enum(1) is always `OTHER: 1`.

        Examples:
        >>> m = Mapping()
        >>> list(m.enum) # [<MappingEnum.OTHER: 1>]
        >>> m = Mapping(hello='你好', world='世界')
        >>> list(m.enum) # [<MappingEnum.OTHER: 1>, <MappingEnum.HELLO: 2>, <MappingEnum.WORLD: 3>]
        """
        return self._enum

    def get_enum_from_label(
        self, label: str, lang: Literal["en", "zh"] = "en"
    ) -> IntEnum:
        """Get the label's enum.

        Args:
            label: Label name.
            lang: Language.
        """
        try:
            match lang.lower():
                case "en":
                    return self.enum[label.upper()]
                case "zh":
                    return self.enum[self.get_en_label(label, fmt="upper")]
                case _:
                    return self.enum[label.upper()]
        except KeyError:
            return self.enum["OTHER"]

    def get_label_from_enum(
        self,
        enum_const: IntEnum,
        lang: Literal["en", "zh"] = "en",
        fmt: Literal["upper", "title", "lower"] = "lower",
    ) -> str:
        """Get enum's label."""
        en_label = enum_const.name.lower()
        lang = lang.lower()
        if lang == "zh":
            return self.en_zh_mapping[en_label]
        else:
            match fmt.lower():
                case "upper":
                    return en_label.upper()
                case "title":
                    return en_label.title()
                case "lower":
                    return en_label
                case _:
                    return en_label

    @property
    def en_zh_mapping(self) -> dict[str, str]:
        """English(lower case) -> Chinese mapping dict."""
        return self._en_zh

    @property
    def zh_en_mapping(self) -> dict[str, str]:
        """Chinese -> English(lower case) mapping dict."""
        return self._zh_en

    def get_en_label(
        self,
        chinese_label: str,
        fmt: Literal["lower", "upper", "title"] = "lower",
    ) -> str:
        """Get English label in specified format.

        Args:
            chinese_label: Chinese label to look up.
            fmt: Output case: lower, upper, or title. Default is lower.
        """
        en = self.zh_en_mapping.get(chinese_label, "other")
        match fmt.lower():
            case "lower":
                return en
            case "upper":
                return en.upper()
            case "title":
                return en.title()
            case _:
                return en

    def get_zh_label(self, english_label: str) -> str:
        """Get Chinese label from English label.

        Args:
            english_label: English label to look up.
        """
        return self.en_zh_mapping.get(english_label.lower(), "其他")

    def __str__(self):
        kwargs = ", ".join(f"{k}={v}" for k, v in self.en_zh_mapping.items())
        return f"<Class {self.__class__.__name__}({kwargs})>"


#############
# Constants #
#############

GENRE: Mapping = Mapping(
    magic="魔幻",
    fantasy="玄幻",
    ancient="古风",
    sf="科幻",
    school="校园",
    urban="都市",
    game="游戏",
    doujin="同人",
    mystery="悬疑",
)

STATUS: Mapping = Mapping(
    finished="已完结",
    on_going="连载中",
    # Fake labels for implicit statuses
    died="断更",
    active_f="活跃F",  # finished but active
    active_d="活跃D",  # died but active
)

PTYPE: Mapping = Mapping(
    free="免费",
    sign="签约",
    vip="VIP",
)


__all__ = ["Mapping", "GENRE", "STATUS", "PTYPE"]


if __name__ == "__main__":
    # print(STATUS)
    # print(GENRE)
    # print(PTYPE)
    # print(repr(PTYPE.enum))
    # print(list(PTYPE.enum))
    # print(repr(STATUS.enum))
    # print(list(STATUS.enum))
    # print(PTYPE.enum(1))
    # m = Mapping()
    # print(list(m.enum))
    m = Mapping(hello="你好", world="世界")
    # print(list(m.enum))
    e = m.get_enum_from_label("hhh", lang="en")
    # print(type(e))
    # print(e.name)
    l = m.get_label_from_enum(m.enum(2), lang="kkk", fmt="title")
    print(l)
    print(m.en_zh_mapping)
    print(m.zh_en_mapping)
    print(m.get_en_label("hggh", fmt="upper"))
    print(m.get_zh_label("hggh"))
    print(m)
