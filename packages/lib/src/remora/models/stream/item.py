import re
from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self
from urllib.parse import urljoin

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

from remora.models._base import Impersonate, RemoraModel, YDLSerializable, rgetattr
from remora.models.container import (
    AudioCodecFamily,
    AVContainer,
    CodecInfo,
    VideoCodecFamily,
)
from remora.models.cookies import CookieList
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


# REQUEST
class StreamRequestContext(RemoraModel):
    data: Annotated[bytes | None, Field(alias="request_data")] = None
    headers: Annotated[dict | None, Field(alias="http_headers")] = None
    cookies: CookieList | None = None
    impersonate: Impersonate = False
    downloader: Annotated[dict | None, Field(alias="downloader_options")] = None


# FRAGMENTS
class StreamFragment(RemoraModel):
    url: HttpUrl
    duration: float | None = None
    size_bytes: Annotated[float | None, Field(alias="filesize")] = None


# STREAMS
class _BaseStream(ABC, YDLSerializable):
    """Base Stream"""

    id: str
    protocol: Protocol
    url: HttpUrl
    fragments: list[StreamFragment] | None = None
    request_context: StreamRequestContext = StreamRequestContext()

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

    @model_validator(mode="after")
    def _build_container_and_extension(self) -> Self:
        raw_ext = self.extension
        container = AVContainer(raw_ext)

        # Mutate the extension field to hold the normalized value
        self.container = container
        self.extension = container.extension
        return self

    # YDL parser/normalizer

    @override
    def _to_ydl_dict(self):
        return {
            # Http Info
            "format_id": self.id,
            "protocol": str(self.protocol),
            "url": str(self.url),
            "fragments": [f.model_dump(by_alias=True) for f in self.fragments]
            if self.fragments
            else None,
            # Basic Container Info
            "filesize": self.size_bytes if self.size_type == "exact" else None,
            "filesize_approx": self.size_bytes
            if self.size_type == "estimated"
            else None,
            "ext": self.extension,
            # Detailed Info
            "vcodec": rgetattr(self, "video.codec.original", "none"),
            "acodec": rgetattr(self, "audio.codec.original", "none"),
            "vbr": rgetattr(self, "video.bitrate", None),
            "abr": rgetattr(self, "audio.bitrate", None),
            "width": rgetattr(self, "video.resolution.width", None),
            "height": rgetattr(self, "video.resolution.height", None),
            # Request Context
            "request_data": self.request_context.data,
            "http_headers": self.request_context.headers,
            "cookies": self.request_context.cookies.to_cookie_header()
            if self.request_context.cookies
            else None,
            "impersonate": self.request_context.impersonate,
            "downloader_options": self.request_context.downloader,
        }

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if _is_ydl_format(data):
            data["id"] = data.get("format_id")
            data["request_context"] = {
                **data,
                "cookies": CookieList.from_cookie_header(cookies)
                if (cookies := data.get("cookies"))
                else None,
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

            # Map resolution
            if data.get("width") and data.get("height"):
                resolution = Resolution._from_ydl_dict(data)
            else:
                resolution = None

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

            # Map fragments
            if fragments := data.get("fragments"):
                base_url = data.get("fragment_base_url")

                for index, item in enumerate(fragments):
                    url = item.get("url")
                    path = item.get("path")

                    if url:
                        absolute_url = url
                    elif base_url and path:
                        absolute_url = urljoin(str(base_url), path)
                    else:
                        raise ValueError("Unable to calculate absolute fragment URL")

                    fragments[index]["url"] = absolute_url
                data["fragments"] = fragments

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


StreamQuality = Literal[144, 240, 360, 480, 720, 1080]

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
