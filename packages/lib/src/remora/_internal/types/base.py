from enum import StrEnum
from typing import Literal


class ExtensionType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


ExtensionTypeStr = Literal["video", "audio"]
ExtensionTypeLike = ExtensionType | ExtensionTypeStr


class BaseExtension:
    @classmethod
    def get_safe_extensions(cls):
        return [e.value for e in cls if e.is_safe]

    @property
    def is_safe(self) -> bool:
        return False

    @property
    def is_common(self) -> bool:
        return False

    @property
    def type(self) -> ExtensionType:
        raise NotImplementedError()

    @property
    def supports_thumbnails(self) -> bool:
        return False

    @property
    def supports_subtitles(self) -> bool:
        return False
