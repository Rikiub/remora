from os import PathLike
from typing import Literal

from pydantic import HttpUrl

# FORMAT
VIDEO_EXTENSION = Literal["mp4", "mkv", "mov"]
AUDIO_EXTENSION = Literal["m4a", "opus", "mp3"]
EXTENSION = Literal[VIDEO_EXTENSION, AUDIO_EXTENSION]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FORMAT_TYPE = Literal["video", "audio"]
FILE_FORMAT = Literal[FORMAT_TYPE, EXTENSION]
VIDEO_RESOLUTION = Literal[144, 240, 360, 480, 720, 1080]

# SEARCH
SEARCH_SERVICE = Literal["soundcloud", "youtube", "ytmusic"]

# Extra
APP_NAME = "remora"
LOGGING_LEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

StrPath = str | PathLike[str]
StrUrl = str | HttpUrl
