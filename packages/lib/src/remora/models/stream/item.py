from abc import ABC
from typing import Annotated, Any, Literal

from pydantic import (
    BeforeValidator,
    Discriminator,
    Field,
    HttpUrl,
    Tag,
    model_validator,
)
from typing_extensions import override

from remora.models._base import RemoraBaseModel, Resolution, YDLSerializable
from remora.models.format.audio import AudioExtension
from remora.models.format.protocol import Protocol
from remora.models.format.type import FormatKind
from remora.models.format.video import VideoExtension
from remora.models.stream.type import StreamKind


def _normalize_codec(value: str | None) -> str | None:
    return None if value == "none" else value


_Codec = Annotated[str, BeforeValidator(_normalize_codec)]
SizeType = Literal["exact", "estimated", "unknown"]


# INFO
class AudioInfo(RemoraBaseModel):
    codec: Annotated[_Codec, Field(alias="acodec")]
    bitrate: Annotated[float | None, Field(alias="abr")] = None
    language: str | None = None


class VideoInfo(RemoraBaseModel):
    codec: Annotated[_Codec, Field(alias="vcodec")]
    bitrate: Annotated[float | None, Field(alias="vbr")] = None
    resolution: Resolution | None = None
    fps: float | None = None


# STREAMS
class YDLOptions(RemoraBaseModel):
    downloader: Annotated[dict, Field(alias="downloader_options")] = {}
    headers: Annotated[dict, Field(alias="http_headers")] = {}
    cookies: str | None = None


class BaseStream(ABC, YDLSerializable):
    """Base Stream"""

    type: Any
    id: Annotated[str, Field(alias="format_id")]

    protocol: Protocol
    url: HttpUrl

    ydl_options: YDLOptions

    extension: Any
    size_type: SizeType = "unknown"
    size_bytes: int | None = None

    @override
    def to_ydl_dict(self):
        data = super().to_ydl_dict()

        # Convert size
        name = "filesize" if self.size_type == "estimated" else "filesize_approx"
        data[name] = self.size_bytes

        # Convert YDL options
        data |= data.get("ydl_options") or {}

        # Flatterize video and audio
        video = data.get("video")
        audio = data.get("audio")

        if video and (vcodec := video.get("vcodec")):
            data |= {
                **video,
                **data.get("resolution", {}),
                "vcodec": vcodec if vcodec else "none",
            }

        if audio and (acodec := audio.get("vcodec")):
            data |= {**audio, "acodec": acodec if acodec else "none"}

        if video and audio:
            data["video_ext"] = video["ext"]
            data["audio_ext"] = audio["ext"]

        # Return normalized info dict
        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if isinstance(data, dict):
            data["ydl_options"] = {
                "downloader": data.get("downloader_options", {}),
                "headers": data.get("http_headers", {}),
                "cookies": data.get("cookies"),
            }

            # Map size
            size_type: SizeType
            filesize = data.get("filesize")
            filesize_approx = data.get("filesize_approx")

            if filesize:
                size_type = "exact"
                size_bytes = filesize
            elif filesize_approx:
                size_type = "estimated"
                size_bytes = filesize_approx
            else:
                size_type = "unknown"
                size_bytes = None

            data["size_type"] = size_type
            data["size_bytes"] = size_bytes

            return data
        return data


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

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_audio(cls, data) -> dict:
        if isinstance(data, dict):
            return {
                **data,
                "audio": data,
            }
        return data


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

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_video(cls, data) -> dict:
        if isinstance(data, dict):
            # Map resolution
            resolution = None
            width = data.get("width")
            height = data.get("height")

            if width and height:
                resolution = {
                    "width": width,
                    "height": height,
                }

            return {
                **data,
                "video": {
                    **data,
                    "resolution": resolution,
                },
            }
        return data


class MuxedStream(VideoStream, AudioStream):
    type: Literal[StreamKind.MUXED] = StreamKind.MUXED  # type: ignore
    extension: Annotated[VideoExtension, Field(alias="ext")]  # type: ignore


def _infer_stream_type(data) -> str:
    video = None
    audio = None

    if isinstance(data, dict):
        video = _normalize_codec(data.get("video") or data.get("vcodec"))
        audio = _normalize_codec(data.get("audio") or data.get("acodec"))
    if isinstance(data, VideoStream):
        video = _normalize_codec(data.video.codec)
    if isinstance(data, AudioStream):
        audio = _normalize_codec(data.audio.codec)

    if video and audio:
        return StreamKind.MUXED
    elif video:
        return StreamKind.VIDEO
    elif audio:
        return StreamKind.AUDIO
    raise ValueError("Cannot determine stream type")


Stream = Annotated[
    Annotated[
        MuxedStream,
        Tag(StreamKind.MUXED),
    ]
    | Annotated[
        VideoStream,
        Tag(StreamKind.VIDEO),
    ]
    | Annotated[
        AudioStream,
        Tag(StreamKind.AUDIO),
    ],
    Discriminator(_infer_stream_type),
]
