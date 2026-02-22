from enum import StrEnum
from typing import Generic, Literal, TypeVar


class ExtensionType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


ExtensionTypeStr = Literal["video", "audio"]
ExtensionTypeLike = ExtensionType | ExtensionTypeStr

T = TypeVar("T", bound=ExtensionType)


class BaseExtension(Generic[T]):
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
    def type(self) -> T:
        return T

    @property
    def supports_thumbnails(self) -> bool:
        return False

    @property
    def supports_subtitles(self) -> bool:
        return False
