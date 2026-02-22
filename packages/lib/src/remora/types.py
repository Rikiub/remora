# ruff: noqa: F401

from os import PathLike
from typing import Literal

from pydantic import HttpUrl

from remora._internal.types.extension import (
    AudioExtension,
    AudioExtensionLike,
    ExtensionType,
    ExtensionTypeLike,
    StreamExtension,
    StreamExtensionLike,
    VideoExtension,
    VideoExtensionLike,
)

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
