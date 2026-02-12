from abc import ABC, abstractmethod
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    HttpUrl,
    SerializerFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
)
from remora.models.base import YDLSerializable
from remora.ydl.types import SupportedExtensions, YDLFormatInfo
from typing_extensions import override

Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]
AudioCodecField = Field(alias="acodec")


class YDLArgs(BaseModel):
    downloader_options: Annotated[dict, Field(default_factory=dict, repr=False)]
    http_headers: Annotated[dict, Field(default_factory=dict, repr=False)]
    cookies: str | None = None


class Stream(ABC, YDLArgs, YDLSerializable):
    """Base Stream"""

    id: Annotated[str, Field(alias="format_id")]
    url: HttpUrl
    protocol: str
    extension: Annotated[str, Field(alias="ext")]
    filesize: int | None = None
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
    audio_codec: Annotated[  # type: ignore
        Codec, AudioCodecField
    ]

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

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.audio:
            raise ValueError(f"{value} not is a valid extension.")
        return value


class VideoStream(Stream):
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

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.video:
            raise ValueError(f"{value} not is a valid extension.")
        return value
