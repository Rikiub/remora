from enum import Enum
from typing import Any

from yt_dlp.downloader import PROTOCOL_MAP  # type: ignore
from yt_dlp.utils import MEDIA_EXTENSIONS


class SupportedExtensions(frozenset[str], Enum):
    """Sets of file extensions supported by YT-DLP."""

    video = frozenset(MEDIA_EXTENSIONS.video)
    audio = frozenset(MEDIA_EXTENSIONS.audio)


SupportedProtocols = frozenset[str](PROTOCOL_MAP.keys())
ThumbnailSupport = frozenset[str](
    {
        "mp3",
        "mkv",
        "mka",
        "mp4",
        "m4a",
        "m4v",
        "mov",
        "ogg",
        "opus",
        "flac",
    }
)


YDLDict = dict[str, Any]
YDLExtractInfo = dict[str, Any]
YDLFormatInfo = dict[str, Any]
YDLParams = dict[str, Any]
