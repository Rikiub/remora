from enum import StrEnum
from typing import Literal

from typing_extensions import override

from remora.models.container.extension._base import BaseExtension
from remora.models.container.format import FormatType


class VideoExtension(BaseExtension, StrEnum):
    # Common
    AVI = "avi"
    FLV = "flv"
    MKV = "mkv"
    MOV = "mov"
    MP4 = "mp4"
    WEBM = "webm"

    # Extra
    V3G2 = "3g2"
    V3GP = "3gp"
    F4V = "f4v"
    MK3D = "mk3d"
    DIVX = "divx"
    MPG = "mpg"
    OGV = "ogv"
    M4V = "m4v"
    WMV = "wmv"

    @property
    def type(self) -> FormatType:
        return "video"

    @property
    def is_safe(self) -> bool:
        return self in {
            VideoExtension.MP4,
            VideoExtension.MKV,
        }

    @property
    @override
    def is_common(self) -> bool:
        return self in {
            VideoExtension.AVI,
            VideoExtension.FLV,
            VideoExtension.MKV,
            VideoExtension.MOV,
            VideoExtension.MP4,
            VideoExtension.WEBM,
        }

    @property
    @override
    def supports_thumbnails(self) -> bool:
        """Checks if the container reliably supports embedded cover art."""
        return self in {
            VideoExtension.MKV,
            VideoExtension.MP4,
            VideoExtension.M4V,
            VideoExtension.MOV,
        }

    @property
    @override
    def supports_subtitles(self) -> bool:
        """Checks if the container supports internal subtitles."""
        return self in {VideoExtension.MKV, VideoExtension.MP4, VideoExtension.WEBM}


SafeVideoExtensionStr = Literal["mp4", "mkv"]
VideoExtensionStr = Literal[
    # Common
    "avi",
    "flv",
    "mkv",
    "mov",
    "mp4",
    "webm",
    # Extra
    "3g2",
    "3gp",
    "f4v",
    "mk3d",
    "divx",
    "mpg",
    "ogv",
    "m4v",
    "wmv",
]

VideoExtensionType = VideoExtension | VideoExtensionStr
