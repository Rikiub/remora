from enum import StrEnum
from typing import Literal


class Protocol(StrEnum):
    RTMP = "rtmp"
    RTMPE = "rtmpe"
    RTMP_FFMPEG = "rtmp_ffmpeg"
    M3U8_NATIVE = "m3u8_native"
    M3U8 = "m3u8"
    MMS = "mms"
    RTSP = "rtsp"
    F4M = "f4m"
    HTTP = "http"
    HTTPS = "https"
    HTTP_DASH_SEGMENTS = "http_dash_segments"
    HTTP_DASH_SEGMENTS_GENERATOR = "http_dash_segments_generator"
    ISM = "ism"
    MHTML = "mhtml"
    NICONICO_LIVE = "niconico_live"
    FC2_LIVE = "fc2_live"
    WEBSOCKET_FRAG = "websocket_frag"
    YOUTUBE_LIVE_CHAT = "youtube_live_chat"
    YOUTUBE_LIVE_CHAT_REPLAY = "youtube_live_chat_replay"
    BUNNYCDN = "bunnycdn"

    @property
    def is_segmented(self) -> bool:
        return self in {
            Protocol.M3U8,
            Protocol.M3U8_NATIVE,
            Protocol.HTTP_DASH_SEGMENTS,
            Protocol.HTTP_DASH_SEGMENTS_GENERATOR,
        }


ProtocolStr = Literal[
    "rtmp",
    "rtmpe",
    "rtmp_ffmpeg",
    "m3u8_native",
    "m3u8",
    "mms",
    "rtsp",
    "f4m",
    "http",
    "https",
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
]
ProtocolLike = Protocol | ProtocolStr
