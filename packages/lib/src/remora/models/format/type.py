from enum import StrEnum
from typing import Literal


class FormatKind(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


FormatKindStr = Literal["video", "audio"]
FormatType = FormatKind | FormatKindStr
