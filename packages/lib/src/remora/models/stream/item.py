import re
from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    Discriminator,
    Field,
    HttpUrl,
    Tag,
    computed_field,
    model_validator,
)
from typing_extensions import override

from remora.models._base import RemoraModel, YDLSerializable, rgetattr
from remora.models.container import (
    AudioCodecFamily,
    AVContainer,
    CodecInfo,
    VideoCodecFamily,
)
from remora.models.metadata import Resolution
from remora.models.protocol import Protocol


def _normalize_value(value: str | None) -> str | None:
    return None if (not value) or (value == "none") else value


def _is_ydl_format(value: dict) -> bool:
    return isinstance(value, dict) and bool(value.get("format_id"))


def _normalize_dynamic_range(value: str) -> str:
    matchs: dict[DynamicRange, str] = {
        "DV": "dv",
        "HDR12": "(hdr)?12",
        "HDR10+": r"(hdr)?10\+",
        "HDR10": "(hdr)?10",
        "HLG": "hlg",
        "SDR": "sdr",
    }
    for key, pattern in matchs.items():
        if re.match(pattern, value.lower()):
            value = key
    return value


DynamicRange = Annotated[
    Literal["DV", "HDR12", "HDR10+", "HDR10", "HLG", "SDR"],
    AfterValidator(_normalize_dynamic_range),
]
SizeType = Literal["exact", "estimated", "unknown"]


# INFO
class AudioInfo(RemoraModel):
    codec: CodecInfo[AudioCodecFamily] | None = None
    bitrate: Annotated[float | None, Field(alias="abr")] = None
    channels: Annotated[int | None, Field(alias="audio_channels")] = None
    sample_rate: Annotated[float | None, Field(alias="asr")] = None
    language: str | None = None


class VideoInfo(RemoraModel):
    codec: CodecInfo[VideoCodecFamily] | None = None
    bitrate: Annotated[float | None, Field(alias="vbr")] = None
    resolution: Resolution | None = None
    fps: float | None = None
    dynamic_range: DynamicRange | str = "SDR"


# STREAMS
class ExtractorMeta(RemoraModel):
    downloader: dict = {}  # noqa: RUF012
    headers: dict = {}  # noqa: RUF012
    cookies: str | None = None


class _BaseStream(ABC, YDLSerializable):
    """Base Stream"""

    id: str
    protocol: Protocol
    url: HttpUrl
    extractor_meta: ExtractorMeta = ExtractorMeta()

    size_type: SizeType = "unknown"
    size_bytes: int | None = None

    container: Annotated[AVContainer, Field(init=False)] = None  # ty: ignore[invalid-assignment]
    extension: Annotated[str, Field(alias="ext")]

    @computed_field
    @property
    def quality(self) -> float:
        """Stream quality."""
        return self._quality()

    @abstractmethod
    def _quality(self) -> float:
        """Stream quality implementation."""
        raise NotImplementedError()

    # Container builder

    @property
    @abstractmethod
    def _has_video(self) -> bool: ...

    @property
    @abstractmethod
    def _audio_codec(self) -> CodecInfo | None: ...

    @model_validator(mode="after")
    def _build_container_and_extension(self) -> Self:
        raw_ext = self.extension

        # Compute the container using the raw value
        container = AVContainer(raw_ext)
        normalized_ext = container.get_extension(
            has_video=self._has_video,
            audio_codec=self._audio_codec.normalized if self._audio_codec else None,
        )

        # Mutate the extension field to hold the normalized value
        self.container = container
        self.extension = normalized_ext
        return self

    # YDL parser/normalizer

    @override
    def _to_ydl_dict(self):
        return {
            "format_id": self.id,
            "url": str(self.url),
            "filesize": self.size_type,
            "filesize_approx": self.size_type,
            "protocol": str(self.protocol),
            "downloader_options": self.extractor_meta.downloader,
            "cookies": self.extractor_meta.cookies,
            "http_headers": self.extractor_meta.headers,
            "ext": self.extension,
            "vcodec": rgetattr(self, "video.codec.original") or "none",
            "acodec": rgetattr(self, "audio.codec.original") or "none",
            "vbr": rgetattr(self, "video.bitrate"),
            "abr": rgetattr(self, "audio.bitrate"),
        }

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if _is_ydl_format(data):
            data["id"] = data.get("format_id")
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
            data.pop("container", None)

            ext = _normalize_value(data.get("ext"))
            audio_ext = _normalize_value(data.get("audio_ext"))
            video_ext = _normalize_value(data.get("video_ext"))

            audio_codec = _normalize_value(data.get("acodec"))
            video_codec = _normalize_value(data.get("vcodec"))
            is_muxed = audio_codec and video_codec

            if is_muxed or audio_codec:
                data["audio"] = {
                    **data,
                    "codec": {"original": audio_codec},
                    "audio_ext": audio_ext or ext,
                }
            if is_muxed or video_codec:
                data["video"] = {
                    **data,
                    "codec": {"original": video_codec},
                    "video_ext": video_ext or ext,
                    "resolution": resolution,
                }

            # Return normalized dict
            return data
        return data


class AudioStream(_BaseStream):
    type: Literal["audio"] = "audio"
    audio: AudioInfo = AudioInfo()

    @property
    @override
    def _has_video(self) -> bool:
        return False

    @property
    @override
    def _audio_codec(self) -> CodecInfo[AudioCodecFamily] | None:
        return self.audio.codec

    @override
    def _quality(self) -> float:
        if b := self.audio.bitrate:
            return b
        return 0


class VideoStream(_BaseStream):
    type: Literal["video"] = "video"
    video: VideoInfo = VideoInfo()

    @override
    def _quality(self) -> float:
        if res := self.video.resolution:
            return res.height
        return 0

    @property
    @override
    def _has_video(self) -> bool:
        return True

    @property
    @override
    def _audio_codec(self) -> None:
        return None


class MuxedStream(VideoStream, AudioStream):
    type: Literal["muxed"] = "muxed"


def _infer_stream_type(data) -> str:
    extension = None
    video = None
    audio = None

    if isinstance(data, dict):
        extension = data.get("ext") or data.get("extension")

        if _is_ydl_format(data):
            video = _normalize_value(data.get("vcodec"))
            audio = _normalize_value(data.get("acodec"))
        else:
            video = data.get("video")
            audio = data.get("audio")
    if isinstance(data, VideoStream):
        extension = data.container
        video = data.video.codec
    if isinstance(data, AudioStream):
        extension = data.container
        audio = data.audio.codec

    # Determine from codec
    if video and audio:
        return "muxed"
    elif video:
        return "video"
    elif audio:
        return "audio"

    # Determine from extension as fallback
    elif extension and (container := AVContainer.get(extension)):
        if container.is_audio_only:
            return "audio"
        else:
            return "video"

    # Else raise error
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
