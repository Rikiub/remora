from enum import StrEnum
from typing import Literal


class StreamKind(StrEnum):
    MUXED = "muxed"
    VIDEO = "video"
    AUDIO = "audio"

    def has_video(self) -> bool:
        if self == (StreamKind.VIDEO, StreamKind.MUXED):
            return True
        return False

    def has_audio(self) -> bool:
        if self == (StreamKind.AUDIO, StreamKind.MUXED):
            return True
        return False


StreamKindStr = Literal["muxed", "video", "audio"]
StreamType = StreamKind | StreamKindStr
