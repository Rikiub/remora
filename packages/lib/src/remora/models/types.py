from os import PathLike

from pydantic import HttpUrl

__all__ = [
    "StrPath",
    "StrUrl",
]

StrPath = PathLike[str] | str
StrUrl = HttpUrl | str
