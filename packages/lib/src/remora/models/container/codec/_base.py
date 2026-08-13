from abc import abstractmethod
from enum import StrEnum
from typing import Self


class BaseCodecFamily(StrEnum):
    @classmethod
    def __missing__(cls, value: str) -> Self | None:
        if isinstance(value, str) and (match := cls.match(value)):
            return match
        return None

    @classmethod
    @abstractmethod
    def match(self, value: str) -> Self | None: ...
