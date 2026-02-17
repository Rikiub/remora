from os import PathLike
from typing import Literal

from pydantic import HttpUrl

from remora._internal.ydl.types import AudioExtension as _YDLAudioExtension
from remora._internal.ydl.types import VideoExtension as _YDLVideoExtension
from remora._internal.ydl.types import YDLExtensions as _YDLExtensions

# Extension
VideoExtension = _YDLVideoExtension
AudioExtension = _YDLAudioExtension
StreamExtension = VideoExtension | AudioExtension
"""Common lossy compression containers formats with thumbnail and metadata support."""


class SupportedExtensions:
    """File extensions supported."""

    VIDEO = _YDLExtensions.VIDEO
    AUDIO = _YDLExtensions.AUDIO
    ALL = _YDLExtensions.ALL

    THUMBNAIL = _YDLExtensions.THUMBNAIL


# Target
SearchService = Literal["soundcloud", "youtube", "ytmusic"]
StreamType = Literal["video", "audio"]
StreamTarget = StreamType | StreamExtension

# Quality
AudioQuality = Literal[128, 256, 360]
VideoQuality = Literal[144, 240, 360, 480, 720, 1080]
StreamQuality = VideoQuality | AudioQuality

# Generics
StrPath = str | PathLike[str]
StrUrl = str | HttpUrl

# Extra
APP_NAME = "remora"
DEFAULT_TEMPLATE = "{uploader.name} - {title}"
DEFAULT_RETRIES = 3
