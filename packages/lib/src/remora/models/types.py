from os import PathLike

from pydantic import HttpUrl

StrPath = PathLike[str] | str
StrUrl = HttpUrl | str

__all__ = [
    "StrPath",
    "StrUrl",
]
