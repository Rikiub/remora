from typing import TypedDict

from remora.models.container import (
    AudioCodec,
    AudioExtension,
    VideoCodec,
    VideoExtension,
)
from remora.models.protocol import Protocol
from remora.models.stream import DynamicRange


class RankDict(TypedDict):
    protocol: tuple[Protocol, ...]
    video_extension: tuple[VideoExtension, ...]
    audio_extension: tuple[AudioExtension, ...]
    video_codec: tuple[VideoCodec, ...]
    audio_codec: tuple[AudioCodec, ...]
    dynamic_range: tuple[DynamicRange, ...]


# Ranks sorted from best to worst
RANK: RankDict = {
    "protocol": (
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
    ),
    "video_extension": (
        VideoExtension.MP4,
        VideoExtension.MOV,
        VideoExtension.WEBM,
        VideoExtension.FLV,
    ),
    "audio_extension": (
        AudioExtension.M4A,
        AudioExtension.AAC,
        AudioExtension.MP3,
        AudioExtension.OGG,
        AudioExtension.OPUS,
        AudioExtension.WEBM,
        AudioExtension.WEBA,
    ),
    "video_codec": (
        "av1",
        "vp9",
        "h265",
        "vp8",
        "h264",
        "h263",
        "theora",
    ),
    "audio_codec": (
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
    ),
    "dynamic_range": ("DV", "HDR12", "HDR10+", "HDR10", "HLG", "SDR"),
}
