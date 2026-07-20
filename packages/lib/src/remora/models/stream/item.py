from abc import ABC
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    Field,
    HttpUrl,
)

from remora.models._base import Resolution, YDLSerializable
from remora.models.format.audio import AudioExtension
from remora.models.format.protocol import Protocol
from remora.models.format.type import FormatKind
from remora.models.format.video import VideoExtension

_Codec = Annotated[
    str, BeforeValidator(lambda v: None if isinstance(v, str) and v == "none" else v)
]
SizeType = Literal["exact", "estimated", "unknown"]


# INFO
class AudioInfo(BaseModel):
    codec: Annotated[str | None, Field(alias="acodec")] = None
    bitrate: Annotated[float | None, Field(alias="abr")] = None
    language: str | None = None


class VideoInfo(BaseModel):
    codec: Annotated[str | None, Field(alias="vcodec")] = None
    bitrate: Annotated[float | None, Field(alias="vbr")] = None
    resolution: Resolution | None = None
    fps: float | None = None


# STREAMS
class YDLOptions(BaseModel):
    extra: dict = {}
    headers: Annotated[dict, Field(alias="http_headers")] = {}
    cookies: str | None = None


class BaseStream(ABC, YDLSerializable):
    """Base Stream"""

    type: Any
    url: HttpUrl
    protocol: Protocol
    id: Annotated[str, Field(alias="format_id")]

    size_type: SizeType = "unknown"
    size_bytes: Annotated[
        int | None,
        Field(
            alias="filesize",
            validation_alias=AliasChoices("filesize", "filesize_approx"),
        ),
    ] = None

    ydl_options: YDLOptions


class AudioStream(BaseStream):
    type: Literal[FormatKind.AUDIO] = FormatKind.AUDIO
    extension: Annotated[AudioExtension, Field(alias="ext")]
    audio: AudioInfo

    @property
    def quality(self) -> float:
        if b := self.audio.bitrate:
            return b
        return 0

    @property
    def display_quality(self) -> str:
        return f"{round(self.quality)}kbps"


class VideoStream(BaseStream):
    type: Literal[FormatKind.VIDEO] = FormatKind.VIDEO
    extension: Annotated[VideoExtension, Field(alias="ext")]
    video: VideoInfo

    @property
    def quality(self) -> float:
        if res := self.video.resolution:
            return res.height
        return 0

    @property
    def display_quality(self) -> str:
        return f"{self.quality}p"


class MuxedStream(VideoStream):
    type: Literal[FormatKind.MUXED] = FormatKind.MUXED  # type: ignore
    audio: AudioInfo


Stream = MuxedStream | VideoStream | AudioStream
