from __future__ import annotations

from enum import StrEnum
from typing import Literal

__all__ = ["Protocol", "ProtocolLike"]


class Protocol(StrEnum):
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    HTTP_DASH_SEGMENTS = "HTTP_DASH_SEGMENTS"
    HTTP_DASH_SEGMENTS_GENERATOR = "HTTP_DASH_SEGMENTS_GENERATOR"

    FTPS = "FTPS"
    FTP = "FTP"

    M3U8 = "M3U8"
    M3U8_NATIVE = "M3U8_NATIVE"

    RTMP = "RTMP"
    RTMPE = "RTMPE"
    RTMP_FFMPEG = "RTMP_FFMPEG"
    RTSP = "RTSP"

    F4M = "F4M"
    F4F = "F4F"
    MMS = "MMS"
    ISM = "ISM"

    YOUTUBE_LIVE_CHAT = "YOUTUBE_LIVE_CHAT"
    YOUTUBE_LIVE_CHAT_REPLAY = "YOUTUBE_LIVE_CHAT_REPLAY"
    NICONICO_LIVE = "NICONICO_LIVE"
    FC2_LIVE = "FC2_LIVE"
    BUNNYCDN = "BUNNYCDN"
    WEBSOCKET_FRAGMENT = "WEBSOCKET_FRAGMENT"
    MHTML = "MHTML"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            if value == "websocket_frag":
                value = cls.WEBSOCKET_FRAGMENT
            return cls(value.upper())
        return None

    def _to_ydl(self) -> str:
        value = self.lower()
        if self == self.WEBSOCKET_FRAGMENT:
            value = "websocket_frag"
        return value

    @property
    def is_segmented(self) -> bool:
        return self in {
            Protocol.M3U8,
            Protocol.M3U8_NATIVE,
            Protocol.HTTP_DASH_SEGMENTS,
            Protocol.HTTP_DASH_SEGMENTS_GENERATOR,
        }


_ProtocolLiteral = Literal[
    "rtmp",
    "rtmpe",
    "rtmp_ffmpeg",
    "m3u8_native",
    "m3u8",
    "mms",
    "rtsp",
    "f4m",
    "f4f",
    "http",
    "https",
    "ftps",
    "ftp",
    "http_dash_segments",
    "http_dash_segments_generator",
    "ism",
    "mhtml",
    "niconico_live",
    "fc2_live",
    "websocket_fragment",
    "youtube_live_chat",
    "youtube_live_chat_replay",
    "bunnycdn",
]
ProtocolLike = Protocol | _ProtocolLiteral
