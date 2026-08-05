from abc import ABC
from typing import Annotated, Literal

from pydantic import (
    BeforeValidator,
    Discriminator,
    Field,
    HttpUrl,
    Tag,
    model_validator,
)
from typing_extensions import override

from remora.models._base import RemoraModel, YDLSerializable
from remora.models.container.extension.audio import AudioExtension
from remora.models.container.extension.video import VideoExtension
from remora.models.metadata.size import Resolution
from remora.models.protocol import Protocol


def _normalize_value(value: str | None) -> str | None:
    return None if value == "none" else value


def _is_ydl_format(value: dict) -> bool:
    return isinstance(value, dict) and bool(value.get("format_id"))


StreamType = Literal["muxed", "video", "audio"]
SizeType = Literal["exact", "estimated", "unknown"]


# INFO
class AudioInfo(RemoraModel):
    codec: Annotated[
        str,
        BeforeValidator(_normalize_value),
        Field(alias="acodec"),
    ]
    bitrate: Annotated[float | None, Field(alias="abr")] = None
    channels: Annotated[int | None, Field(alias="audio_channels")] = None
    sample_rate: Annotated[float | None, Field(alias="asr")] = None
    language: str | None = None


class VideoInfo(RemoraModel):
    codec: Annotated[
        str,
        BeforeValidator(_normalize_value),
        Field(alias="vcodec"),
    ]
    bitrate: Annotated[float | None, Field(alias="vbr")] = None
    resolution: Resolution | None = None
    fps: float | None = None


# STREAMS
class ExtractorMeta(RemoraModel):
    downloader: Annotated[dict, Field(alias="downloader_options")] = {}  # noqa: RUF012
    headers: Annotated[dict, Field(alias="http_headers")] = {}  # noqa: RUF012
    cookies: str | None = None


class _BaseStream(ABC, YDLSerializable):
    """Base Stream"""

    type: StreamType
    id: Annotated[str, Field(alias="format_id")]

    protocol: Protocol
    url: HttpUrl
    extractor_meta: ExtractorMeta = ExtractorMeta()

    size_type: SizeType = "unknown"
    size_bytes: int | None = None

    @override
    def _to_ydl_dict(self):
        data = super()._to_ydl_dict()

        # Convert size
        name = "filesize" if self.size_type == "exact" else "filesize_approx"
        data[name] = self.size_bytes

        # Convert YDL options
        data |= data.get("extractor_meta") or {}

        # Flatterize video and audio
        data |= {
            "acodec": "none",
            "vcodec": "none",
        }

        audio = data.get("audio")
        video = data.get("video")

        if audio and (acodec := audio.get("acodec")):
            data |= {
                **audio,
                "acodec": acodec or "none",
            }

        if video and (vcodec := video.get("vcodec")):
            data |= {
                **video,
                **data.get("resolution", {}),
                "vcodec": vcodec or "none",
            }

        # Return normalized info dict
        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if _is_ydl_format(data):
            data["extractor_meta"] = {
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

            # Get resolution
            resolution = None
            width = data.get("width")
            height = data.get("height")

            if width and height:
                resolution = {
                    "width": width,
                    "height": height,
                }

            # Map data to video and audio
            ext = _normalize_value(data.get("ext"))
            audio_ext = _normalize_value(data.get("audio_ext"))
            video_ext = _normalize_value(data.get("video_ext"))

            audio_codec = _normalize_value(data.get("acodec"))
            video_codec = _normalize_value(data.get("vcodec"))
            is_muxed = audio_codec and video_codec

            if is_muxed or audio_codec:
                data["audio"] = {
                    **data,
                    "audio_ext": audio_ext or ext,
                    "acodec": audio_codec,
                }
            if is_muxed or video_codec:
                data["video"] = {
                    **data,
                    "video_ext": video_ext or ext,
                    "vcodec": video_codec,
                    "resolution": resolution,
                }

            # Return normalized dict
            return data
        return data


class AudioStream(_BaseStream):
    type: Literal["audio"] = "audio"
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


class VideoStream(_BaseStream):
    type: Literal["video"] = "video"
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


class MuxedStream(VideoStream, AudioStream):
    type: Literal[StreamType] = "muxed"  # type: ignore
    extension: Annotated[VideoExtension, Field(alias="ext")]  # type: ignore


def _infer_stream_type(data) -> StreamType:
    video = None
    audio = None

    if isinstance(data, dict):
        video = _normalize_value(data.get("video") or data.get("vcodec"))
        audio = _normalize_value(data.get("audio") or data.get("acodec"))
    if isinstance(data, VideoStream):
        video = _normalize_value(data.video.codec)
    if isinstance(data, AudioStream):
        audio = _normalize_value(data.audio.codec)

    if video and audio:
        return "muxed"
    elif video:
        return "video"
    elif audio:
        return "audio"
    raise ValueError("Cannot determine stream type")


Stream = MuxedStream | VideoStream | AudioStream
_DiscriminatedStream = Annotated[
    Annotated[
        MuxedStream,
        Tag("muxed"),
    ]
    | Annotated[
        VideoStream,
        Tag("video"),
    ]
    | Annotated[
        AudioStream,
        Tag("audio"),
    ],
    Discriminator(_infer_stream_type),
]
