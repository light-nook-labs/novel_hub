"""Enums and mappers for SFACG novel metadata."""

from abc import ABC
from enum import IntEnum, unique
from typing import Literal
from string import ascii_letters
import re


CHARACTERS = ascii_letters + "-_"
pattern = re.compile(rf"^[{CHARACTERS}]+$")

class MappingBase(ABC):
    """Maps English attribute names to Chinese(another language) labels."""

    def __init__(self, en_zh_mapping_dict: dict[str, str]):
        self._validate_mapping_dict(en_zh_mapping_dict)
        self._mapping: dict[str, str] = en_zh_mapping_dict
        # Fallback key-value
        self._mapping["other"] = "其他"
        self._en_zh: dict[str, str] = self._mapping
        self._zh_en: dict[str, str] = {v: k for k, v in self._mapping.items()}

    def _validate_mapping_dict(self, en_zh_mapping_dict):
        invalid_keys = [k for k in en_zh_mapping_dict if not pattern.fullmatch(k)]
        if invalid_keys:
            raise ValueError(f"Invalid keys: {invalid_keys}. Keys must consist of ascii letters, '_' or '-'.")

    @property
    def en_zh_mapping(self) -> dict[str, str]:
        """English -> Chinese mapping dict."""
        return self._en_zh

    @property
    def zh_en_mapping(self) -> dict[str, str]:
        """Chinese -> English mapping dict."""
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
        match format.lower():
            case "lower":
                return en.lower()
            case "upper":
                return en.upper()
            case "title":
                return en.title()
            case _:
                return en.lower()

    def get_zh_label(self, english_label: str) -> str:
        """Get Chinese label from English label."""
        return self.en_zh_mapping.get(english_label.lower(), "其他")

    def __str__(self):
        kwargs = ", ".join(f"{k}={v}" for k, v in self._mapping.items())
        return f"<Class {self.__class__.__name__}({kwargs})>"


class GenreMapping(MappingBase):
    magic = "魔幻"
    fantasy = "玄幻"
    ancient = "古风"
    sf = "科幻"
    school = "校园"
    urban = "都市"
    game = "游戏"
    doujin = "同人"
    mystery = "悬疑"


class StatusMapping(MappingBase):
    finished = "已完结"
    on_going = "连载中"

    # Fake labels for implicit statuses
    died = "断更"
    active_f = "活跃F"  # finished but active
    active_d = "活跃D"  # died but active

    def get_zh_label(self, english_label, is_true_label=False):
        """Get Chinese label, optionally collapsing fake labels to real ones.

        When is_true_label is False, active_f and finished both map to
        '已完结'; on_going, died, and active_d all map to '连载中'.
        """
        if is_true_label:
            return super().get_zh_label(english_label)
        if english_label in ("active_f", "finished"):
            return super().get_zh_label("finished")
        if english_label in ("on_going", "died", "active_d"):
            return super().get_zh_label("on_going")
        return super().get_zh_label(english_label)


class PTypeMapping(MappingBase):
    free = "免费"
    sign = "签约"
    vip = "VIP"


@unique
class LabeledIntEnum(IntEnum):
    """Base enum with bilingual label support."""

    _mapping: MappingBase

    @classmethod
    def get_mapping(cls) -> MappingBase:
        return cls._mapping

    def get_label(self, lang="en") -> str:
        match lang.lower():
            case "en":
                return self.name.lower()
            case "zh":
                return self.get_mapping().get_zh_label(self.name.lower())
            case _:
                return self.name.lower()

    @property
    def en_label(self) -> str:
        return self.get_label(lang="en")

    @property
    def zh_label(self) -> str:
        return self.get_label(lang="zh")

    @classmethod
    def from_label(cls, label: str) -> "LabeledIntEnum":
        mapping = cls.get_mapping()
        if label in mapping.zh_en_mapping:
            enum_name = mapping.zh_en_mapping[label].upper()
            return cls[enum_name]
        if label.upper() in cls.__members__:
            return cls[label.upper()]
        return cls.OTHER


class Genre(LabeledIntEnum):
    MAGIC = 1
    FANTASY = 2
    ANCIENT = 3
    SF = 4
    SCHOOL = 5
    URBAN = 6
    GAME = 7
    DOUJIN = 8
    MYSTERY = 9
    OTHER = 99


# Genre._mapping = GenreMapping()


class Status(LabeledIntEnum):
    FINISHED = 1
    ON_GOING = 2
    DIED = 3
    ACTIVE_F = 4
    ACTIVE_D = 5
    OTHER = 99


# Status._mapping = StatusMapping()


class PType(LabeledIntEnum):
    FREE = 1
    SIGN = 2
    VIP = 3
    OTHER = 99


# PType._mapping = PTypeMapping()


if __name__ == '__main__':
    print(pattern.search('GOOD_+'))