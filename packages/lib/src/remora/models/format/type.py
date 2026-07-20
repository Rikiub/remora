from enum import StrEnum
from typing import Literal


class FormatKind(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    MUXED = "muxed"


FormatKindStr = Literal["video", "audio", "muxed"]
FormatType = FormatKind | FormatKindStr
