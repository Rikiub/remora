from abc import ABC, abstractmethod
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AliasChoices,
    BaseModel,
    Field,
    HttpUrl,
    SerializerFunctionWrapHandler,
    field_serializer,
    model_serializer,
)
from typing_extensions import override

from remora.models.base import YDLSerializable
from remora.types import AudioExtension, StreamExtension, VideoExtension
from remora.ydl.types import YDLFormatInfo

Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]
AudioCodecField = Field(alias="acodec")
ExtensionField = Field(alias="ext")


class YDLArgs(BaseModel):
    downloader_options: Annotated[dict, Field(default_factory=dict)]
    http_headers: Annotated[dict, Field(default_factory=dict)]
    cookies: str | None = None


class Stream(ABC, YDLArgs, YDLSerializable):
    """Base Stream"""

    id: Annotated[str, Field(alias="format_id")]
    url: HttpUrl
    protocol: str
    available_at: int | None = None
    extension: Annotated[StreamExtension, Field(alias="ext")]
    filesize: Annotated[
        int | None,
        Field(
            alias="filesize",
            validation_alias=AliasChoices("filesize", "filesize_approx"),
        ),
    ] = None
    bitrate: Annotated[float, Field(alias="tbr")] = 0
    audio_codec: Annotated[Codec | None, AudioCodecField] = None

    def to_ydl_dict(self) -> YDLFormatInfo:
        return super().to_ydl_dict()

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_codec)

    @field_serializer("audio_codec")
    def _serialize_acodec(self, value) -> str:
        return value if value else "none"


class AudioStream(Stream):
    type: Literal["audio"] = "audio"
    extension: Annotated[  # type: ignore
        AudioExtension,
        ExtensionField,
    ]
    audio_codec: Annotated[  # type: ignore
        Codec, AudioCodecField
    ]
    language: str | None = None

    @property
    @override
    def quality(self) -> int:
        return int(self.bitrate)

    @property
    @override
    def display_quality(self) -> str:
        return str(round(self.quality)) + "kbps"

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler):
        result: dict = handler(self)
        result |= {"vcodec": "none"}
        return result


class VideoStream(Stream):
    extension: Annotated[  # type: ignore
        VideoExtension,
        ExtensionField,
    ]
    video_codec: Annotated[Codec, Field(alias="vcodec")]
    type: Literal["video"] = "video"
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
        return str(self.quality) + "p"
