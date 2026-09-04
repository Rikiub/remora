from dataclasses import dataclass
from pathlib import Path
from typing import Generic

from typing_extensions import TypeVar

from remora.models.stream import Stream

_T = TypeVar("_T", bound=Stream, default=Stream)


@dataclass(slots=True)
class StreamContext(Generic[_T]):
    stream: _T
    path: Path

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")
