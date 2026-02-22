from os import PathLike
from typing import Literal

from pydantic import HttpUrl

from remora._internal.ydl.types import AudioExtension as _YDLAudioExtension
from remora._internal.ydl.types import VideoExtension as _YDLVideoExtension
from remora._internal.ydl.types import YDLExtensions as _YDLExtensions

# Stream Extension
VideoExtension = _YDLVideoExtension
AudioExtension = _YDLAudioExtension
StreamExtension = VideoExtension | AudioExtension

# Safe Extension
SafeVideoExtension = Literal["mp4", "mkv"]
"""Common containers compatibles with: merging, remuxing, thumbnails, subtitles and metadata embedding."""

SafeAudioExtension = Literal["m4a", "mp3", "mka", "flac"]
"""Common containers compatibles with: merging, remuxing, thumbnails and metadata embedding."""

SafeExtension = SafeVideoExtension | SafeAudioExtension


class SupportedExtensions:
    """File extensions supported."""

    VIDEO = _YDLExtensions.VIDEO
    AUDIO = _YDLExtensions.AUDIO
    ALL = _YDLExtensions.ALL

    THUMBNAIL = _YDLExtensions.THUMBNAIL


# Target
SearchService = Literal["soundcloud", "youtube", "ytmusic"]
StreamType = Literal["video", "audio"]
StreamTarget = StreamType | SafeExtension

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
