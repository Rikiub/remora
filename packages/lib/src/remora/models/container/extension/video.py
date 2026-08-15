from enum import StrEnum
from typing import Literal

from typing_extensions import override

from remora.models.container.extension._base import BaseContainer


class VideoContainer(BaseContainer, StrEnum):
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
    @override
    def supports_thumbnails(self) -> bool:
        """Checks if container reliably supports embedded cover art."""
        return self in {
            VideoContainer.MKV,
            VideoContainer.MP4,
            VideoContainer.M4V,
            VideoContainer.MOV,
        }

    @property
    @override
    def supports_subtitles(self) -> bool:
        """Checks if container reliably supports embedded subtitles."""
        return self in {
            VideoContainer.MKV,
            VideoContainer.MP4,
            VideoContainer.M4V,
            VideoContainer.MOV,
            VideoContainer.WEBM,
        }


_VideoContainerLiteral = Literal[
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
SafeVideoContainer = Literal["mp4", "mkv"]
VideoContainerLike = VideoContainer | _VideoContainerLiteral
