from os import PathLike

from pydantic import AnyUrl

__all__ = [
    "StrPath",
    "StrUrl",
]

StrPath = PathLike[str] | str
StrUrl = AnyUrl | str
