from abc import abstractmethod
from enum import StrEnum
from typing import Self


class GetterEnum(StrEnum):
    @classmethod
    @abstractmethod
    def get(cls, value: str | None) -> Self | None:
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str) and (member := cls.get(value)):
            return member
        return None
