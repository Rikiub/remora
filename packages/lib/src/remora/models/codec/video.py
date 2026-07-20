from __future__ import annotations

from remora.models.codec._base import Codec


class VideoCodec(Codec):
    AV01 = "av01"
    AVC = "avc"

    VP9_2 = "vp9.2"
    VP9 = "vp9"
    VP8 = "vp8"

    MP4V = "mp4v"
    HEVC = "hevc"
    H265 = "h265"
    H264 = "h264"
    H263 = "h263"

    THEORA = "theora"

    @classmethod
    def by_best(cls) -> list[VideoCodec]:
        return [
            VideoCodec.AV01,
            VideoCodec.VP9_2,
            VideoCodec.VP9,
            VideoCodec.HEVC,
            VideoCodec.H265,
            VideoCodec.VP8,
            VideoCodec.AVC,
            VideoCodec.H264,
            VideoCodec.MP4V,
            VideoCodec.H263,
            VideoCodec.THEORA,
        ]
