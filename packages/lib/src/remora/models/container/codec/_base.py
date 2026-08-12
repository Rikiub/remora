from abc import abstractmethod
from enum import StrEnum
from typing import Self


class BaseCodecFamily(StrEnum):
    @classmethod
    def from_str(cls, value: str) -> Self:
        """Parse string and get codec family."""
        if cls.match(value):
            return value  # ty: ignore[invalid-return-type]
        raise ValueError(value)

    @classmethod
    @abstractmethod
    def match(self, value: str) -> Self | None: ...
