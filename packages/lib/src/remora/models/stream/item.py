from abc import ABC, abstractmethod
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, AliasChoices, BaseModel, Field, HttpUrl
from typing_extensions import override

from remora.models._base import YDLSerializable
from remora.types import AudioExtension, StreamExtension, StreamType, VideoExtension

T_Type = TypeVar("T_Type", bound=StreamType)
T_Ext = TypeVar("T_Ext", bound=StreamExtension)

_Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]
_AudioCodecField = Field(alias="acodec")


class YDLArgs(BaseModel):
    downloader_options: dict = {}
    http_headers: dict = {}
    cookies: str | None = None


class BaseStream(ABC, YDLArgs, YDLSerializable, Generic[T_Type, T_Ext]):
    """Base Stream"""

    url: HttpUrl
    protocol: str
    id: Annotated[str, Field(alias="format_id")]
    type: T_Type
    extension: Annotated[T_Ext, Field(alias="ext")]

    size: Annotated[
        int | None,
        Field(
            alias="filesize",
            validation_alias=AliasChoices("filesize", "filesize_approx"),
        ),
    ] = None
    bitrate: Annotated[float | None, Field(alias="tbr")] = None
    audio_codec: Annotated[_Codec | None, _AudioCodecField] = None

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_codec)

    @override
    def to_ydl_dict(self):
        info = super().to_ydl_dict()

        acodec = info.get("acodec")
        info["acodec"] = acodec if acodec else "none"

        return info


class AudioStream(BaseStream[Literal["audio"], AudioExtension]):
    type: Literal["audio"] = "audio"

    language: str | None = None
    audio_codec: Annotated[  # type: ignore
        _Codec, _AudioCodecField
    ]

    @property
    @override
    def quality(self) -> int:
        return int(self.bitrate) if self.bitrate else 0

    @property
    @override
    def display_quality(self) -> str:
        return f"{round(self.quality)}kbps"

    @override
    def to_ydl_dict(self):
        info = super().to_ydl_dict()
        info |= {"vcodec": "none"}
        return info


class VideoStream(BaseStream[Literal["video"], VideoExtension]):
    type: Literal["video"] = "video"

    video_codec: Annotated[_Codec, Field(alias="vcodec")]
    width: int
    height: int
    fps: float | None = None

    @property
    @override
    def quality(self) -> int:
        return self.height

    @property
    @override
    def display_quality(self) -> str:
        return f"{self.quality}p"


Stream = VideoStream | AudioStream
