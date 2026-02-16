from os import PathLike
from typing import Literal

from pydantic import HttpUrl

from remora.ydl.types import AudioExtension as YDLAudioExtension
from remora.ydl.types import VideoExtension as YDLVideoExtension
from remora.ydl.types import YDLExtensions

# Extension
VideoExtension = YDLVideoExtension
AudioExtension = YDLAudioExtension
StreamExtension = VideoExtension | AudioExtension
"""Common lossy compression containers formats with thumbnail and metadata support."""


class SupportedExtensions:
    """File extensions supported."""

    VIDEO = YDLExtensions.VIDEO
    AUDIO = YDLExtensions.AUDIO
    ALL = YDLExtensions.ALL

    THUMBNAIL = YDLExtensions.THUMBNAIL


# Target
StreamType = Literal["video", "audio"]
StreamTarget = StreamType | StreamExtension

SearchService = Literal["soundcloud", "youtube", "ytmusic"]

# Quality
AudioQuality = Literal[128, 256, 360]
VideoQuality = Literal[144, 240, 360, 480, 720, 1080]
StreamQuality = VideoQuality | AudioQuality

# Generics
StrPath = str | PathLike[str]
StrUrl = str | HttpUrl
LoggingLevels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Extra
APP_NAME = "remora"
