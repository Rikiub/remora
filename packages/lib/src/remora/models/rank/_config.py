from typing import TypedDict

from remora.models.container import (
    AudioCodec,
    AudioExtensionLike,
    VideoCodec,
    VideoExtensionLike,
)
from remora.models.protocol import Protocol
from remora.models.stream import DynamicRange


class _RankDict(TypedDict):
    protocol: list[Protocol]
    video_codec: list[VideoCodec]
    audio_codec: list[AudioCodec]
    video_extension: list[VideoExtensionLike]
    audio_extension: list[AudioExtensionLike]
    dynamic_range: list[DynamicRange]


# Ranks sorted from best to worst
RANK: _RankDict = {
    "protocol": [
        Protocol.HTTPS,
        Protocol.FTPS,
        Protocol.HTTP,
        Protocol.FTP,
        Protocol.M3U8_NATIVE,
        Protocol.M3U8,
        Protocol.HTTP_DASH_SEGMENTS,
        Protocol.WEBSOCKET_FRAG,
        Protocol.MMS,
        Protocol.RTSP,
        Protocol.F4F,
        Protocol.F4M,
    ],
    "video_codec": [
        "av1",
        "vp9",
        "h265",
        "vp8",
        "h264",
        "h263",
        "theora",
    ],
    "audio_codec": [
        "pcm",
        "alac",
        "flac",
        "opus",
        "vorbis",
        "aac",
        "mp3",
        "ac4",
        "dts",
        "eac3",
        "ac3",
    ],
    "video_extension": ["mp4", "mov", "webm", "flv"],
    "audio_extension": ["m4a", "aac", "mp3", "ogg", "opus", "webm", "weba"],
    "dynamic_range": ["DV", "HDR12", "HDR10+", "HDR10", "HLG", "SDR"],
}
