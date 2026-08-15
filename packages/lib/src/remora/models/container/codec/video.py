from __future__ import annotations

import re
from typing import Literal

from typing_extensions import override

from remora.models.container._base import GetterEnum


class VideoCodecFamily(GetterEnum):
    AV1 = "AV1"
    VP9 = "VP9"
    VP8 = "VP8"
    H265 = "H.265"
    H264 = "H.264"
    H263 = "H.263"
    THEORA = "Theora"

    @override
    @classmethod
    def get(cls, value: str | None) -> VideoCodecFamily | None:
        if not value:
            return None
        value = value.lower().strip()

        codec = {member: member.value.lower() for member in cls}
        codec = codec | {
            cls.AV1: r"av0?1",
            cls.VP9: r"vp0?9",
            cls.VP8: r"vp0?8",
            cls.H265: r"[hx]\.?265|he?vc?",
            cls.H264: r"[hx]\.?264|avc",
            cls.H263: r"mp4v|h\.?263",
        }

        for enum, regex in codec.items():
            if re.match(regex, value):
                return enum
        return None


VideoCodec = Literal[
    "av1",
    "vp9",
    "vp8",
    "h265",
    "h264",
    "h263",
    "theora",
]
