from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from remora.models.stream.item import Stream

_T = TypeVar("_T", bound=Stream)


@dataclass(slots=True)
class StreamContext(Generic[_T]):
    stream: _T
    path: Path

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")
