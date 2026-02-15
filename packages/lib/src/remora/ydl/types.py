from enum import Enum
from typing import Any, Final, Literal, get_args

# Video
CommonVideoExtension = Literal["avi", "flv", "mkv", "mov", "mp4", "webm"]
ExtraVideoExtension = Literal[
    "3g2", "3gp", "f4v", "mk3d", "divx", "mpg", "ogv", "m4v", "wmv"
]
VideoExtension = Literal[CommonVideoExtension, ExtraVideoExtension]

# Audio
CommonAudioExtension = Literal[
    "aiff", "alac", "flac", "m4a", "mka", "mp3", "ogg", "opus", "wav"
]
ExtraAudioExtension = Literal[
    "aac",
    "ape",
    "asf",
    "f4a",
    "f4b",
    "m4b",
    "m4r",
    "oga",
    "ogx",
    "spx",
    "vorbis",
    "wma",
    "weba",
]
AudioExtension = Literal[CommonAudioExtension, ExtraAudioExtension]

# Video and Audio
FormatExtension = Literal[VideoExtension, AudioExtension]


class SupportedExtensions(frozenset[str], Enum):
    """Sets of file extensions supported by YT-DLP."""

    VIDEO = frozenset(get_args(VideoExtension))
    AUDIO = frozenset(get_args(AudioExtension))
    ALL = frozenset(get_args(FormatExtension))


THUMBNAIL_SUPPORT: Final = frozenset[str](
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
SUPPORTED_PROTOCOLS: Final = frozenset(
    {
        "rtmp",
        "rtmpe",
        "rtmp_ffmpeg",
        "m3u8_native",
        "m3u8",
        "mms",
        "rtsp",
        "f4m",
        "http_dash_segments",
        "http_dash_segments_generator",
        "ism",
        "mhtml",
        "niconico_live",
        "fc2_live",
        "websocket_frag",
        "youtube_live_chat",
        "youtube_live_chat_replay",
        "bunnycdn",
    }
)

YDLDict = dict[str, Any]
YDLExtractInfo = dict[str, Any]
YDLFormatInfo = dict[str, Any]
YDLParams = dict[str, Any]
