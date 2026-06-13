"""Mappings: English keys ↔ Chinese labels, backed by IntEnum.

Import these constants for data loading and template context.
"""

from enum import IntEnum


class Mapping:
    """Bidirectional en↔zh label mapping with IntEnum.

    Index 1 is always OTHER/其他 (fallback).
    Unknown lookups silently return OTHER.
    """

    def __init__(self, **en_zh):
        self._en_zh: dict[str, str] = {"other": "其他"}
        self._zh_en: dict[str, str] = {"其他": "other"}
        for en, zh in en_zh.items():
            self._en_zh[en.lower()] = zh
            self._zh_en[zh] = en.lower()
        names = ["OTHER"] + [k.upper() for k in en_zh]
        self._enum = IntEnum(f"{self.__class__.__name__}Enum", names)

    @property
    def enum(self) -> IntEnum:
        return self._enum

    @property
    def choices(self) -> list[tuple[int, str]]:
        """Return [(value, zh_label), ...] for Django form/template use."""
        return [(m.value, self._en_zh.get(m.name.lower(), m.name)) for m in self._enum]

    def get_value(self, zh_label: str) -> int:
        """Chinese label → enum int value. Falls back to OTHER."""
        en = self._zh_en.get(zh_label, "other")
        return self._enum[en.upper()].value

    def get_zh(self, value: int) -> str:
        """Enum int value → Chinese label."""
        try:
            member = self._enum(value)
            return self._en_zh.get(member.name.lower(), "其他")
        except ValueError:
            return "其他"

    def zh_labels(self) -> list[str]:
        """Return all Chinese labels."""
        return list(self._zh_en.keys())

    def en_keys(self) -> list[str]:
        """Return all English keys (excluding 'other')."""
        return [k for k in self._en_zh if k != "other"]

    def zh_to_value_dict(self) -> dict[str, int]:
        """Return {zh_label: value} mapping for pandas .map()."""
        return {zh: self.get_value(zh) for zh in self._zh_en}

    def fallback(self) -> int:
        """Return OTHER enum value."""
        return self._enum.OTHER.value


GENRE = Mapping(
    magic="魔幻",
    eastern="玄幻",
    ancient="古风",
    sci_fi="科幻",
    school="校园",
    urban="都市",
    game="游戏",
    doujin="同人",
    mystery="悬疑",
)

STATUS = Mapping(
    finished="已完结",
    on_going="连载中",
    died="断更",
    active_d="断更D",
    active_f="完结F",
)

PTYPE = Mapping(
    free="免费",
    sign="签约",
    vip="VIP",
)
