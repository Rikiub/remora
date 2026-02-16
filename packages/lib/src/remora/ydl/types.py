from typing import Any, Final, Literal

from remora.helpers import literal_to_set

# Video
CommonVideoExtension = Literal["avi", "flv", "mkv", "mov", "mp4", "webm"]
ExtraVideoExtension = Literal[
    "3g2", "3gp", "f4v", "mk3d", "divx", "mpg", "ogv", "m4v", "wmv"
]
VideoExtension = CommonVideoExtension | ExtraVideoExtension

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
AudioExtension = CommonAudioExtension | ExtraAudioExtension

# Video and Audio
FormatExtension = VideoExtension | AudioExtension


class YDLExtensions:
    """Sets of format extensions supported by YT-DLP."""

    VIDEO: Final = literal_to_set(VideoExtension)
    AUDIO: Final = literal_to_set(AudioExtension)
    ALL: Final = literal_to_set(FormatExtension)

    THUMBNAIL: Final = frozenset(
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


YDL_PROTOCOLS: Final = frozenset(
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
