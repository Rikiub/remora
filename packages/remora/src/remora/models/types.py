from os import PathLike
from typing import Any

from pydantic import AnyUrl

__all__ = ["AnyDict", "StrPath", "StrUrl"]

StrPath = PathLike[str] | str
StrUrl = AnyUrl | str
AnyDict = dict[str, Any]
