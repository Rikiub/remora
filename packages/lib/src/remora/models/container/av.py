from __future__ import annotations

from abc import abstractmethod
from typing import Literal, Self

from typing_extensions import override

from remora.models.container._base import GetterEnum


class _BaseContainer(GetterEnum):
    @property
    def extension(self) -> str:
        return self.value.lower()

    @property
    @abstractmethod
    def supports_subtitles(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def supports_thumbnails(self) -> bool:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _map_dict(cls) -> dict[str, Self]:
        raise NotImplementedError

    @override
    @classmethod
    def get(cls, value: str | None) -> Self | None:
        if not value:
            return None
        value = value.lower().lstrip(".").strip()

        if member := cls._map_dict().get(value):
            return member

        for member in cls:
            if member.lower() == value.lower():
                return member

        return None


class VideoContainer(_BaseContainer):
    AVI = "AVI"
    FLV = "FLV"
    MP4 = "MP4"
    MOV = "MOV"
    V3GP = "3GP"
    MKV = "MKV"
    WEBM = "WEBM"
    OGV = "OGV"
    MPG = "MPG"
    TS = "TS"
    WMV = "WMV"

    @override
    @property
    def supports_subtitles(self) -> bool:
        """Checks if container reliably supports embedded subtitles."""
        return self in {
            VideoContainer.MKV,
            VideoContainer.MP4,
            VideoContainer.MOV,
        }

    @override
    @property
    def supports_thumbnails(self) -> bool:
        """Checks if container reliably supports embedded cover art."""
        return self in {
            VideoContainer.MKV,
            VideoContainer.MP4,
            VideoContainer.MOV,
        }

    @override
    @classmethod
    def _map_dict(cls):
        return _VIDEO_MAP


class AudioContainer(_BaseContainer):
    AIFF = "AIFF"
    FLAC = "FLAC"
    OGG = "OGG"
    MKA = "MKA"
    M4A = "M4A"
    MP3 = "MP3"
    WAV = "WAV"
    AAC = "AAC"
    APE = "APE"
    WEBA = "WEBA"

    @override
    @property
    def supports_subtitles(self) -> bool:
        """Checks if container reliably supports embedded subtitles."""
        return self in {
            AudioContainer.MKA,
            AudioContainer.M4A,
        }

    @override
    @property
    def supports_thumbnails(self) -> bool:
        """Checks if container reliably supports embedded cover art."""
        return self in {
            AudioContainer.MKA,
            AudioContainer.M4A,
            AudioContainer.MP3,
            AudioContainer.FLAC,
        }

    @override
    @classmethod
    def _map_dict(cls):
        return _AUDIO_MAP


AVContainer = VideoContainer | AudioContainer


def get_container(value: str | None) -> AVContainer:
    container = VideoContainer.get(value) or AudioContainer.get(value)
    if not container:
        raise ValueError(f"'{value}' is a invalid container")
    return container


# Mapping extensions/aliases to canonical Enum values
_VIDEO_MAP: dict[str, VideoContainer] = {
    alias: canonical
    for canonical, aliases in {
        VideoContainer.MP4: (
            # Apple extensions
            "m4v",
            "m4b",
            "m4r",
            "alac",
            # Flash extensions
            "f4v",
            "f4a",
            "f4b",
            # Standard MPEG-4 aliases
            "mpg4",
            "mp4v",
        ),
        VideoContainer.MOV: ("qt", "quicktime"),
        VideoContainer.V3GP: ("3gpp", "3g2", "3gpp2"),
        VideoContainer.MKV: ("mk3d",),
        VideoContainer.TS: ("m2ts", "mts"),
        VideoContainer.MPG: ("mpeg", "m2v", "m2p", "mpe", "vob"),
        VideoContainer.WMV: ("wma", "asf"),
    }.items()
    for alias in aliases
}
_AUDIO_MAP: dict[str, AudioContainer] = {
    alias: canonical
    for canonical, aliases in {
        AudioContainer.OGG: ("oga", "ogx", "opus", "vorbis", "spx"),
        AudioContainer.AIFF: ("aif", "aifc"),
        AudioContainer.WAV: ("wave",),
        AudioContainer.APE: ("mac",),
        AudioContainer.MP3: ("mpeg3", "mpg3", "mp1", "mp2"),
    }.items()
    for alias in aliases
}

# Specializations
# Mostly for autocompletion

VideoContainerLike = (
    VideoContainer
    | Literal[
        "avi",
        "flv",
        "mp4",
        "mov",
        "3gp",
        "mkv",
        "webm",
        "ogv",
        "mpg",
        "ts",
        "wmv",
    ]
)
"""Common video containers."""

AudioContainerLike = (
    AudioContainer
    | Literal[
        "aiff",
        "flac",
        "ogg",
        "opus",
        "mka",
        "m4a",
        "mp3",
        "wav",
        "aac",
        "ape",
    ]
)
"""Common audio-only containers."""

AVContainerLike = AVContainer | VideoContainerLike | AudioContainerLike
"""Common video and audio-only containers."""

# Rich specializations
# Recommended safe containers

RichAudioContainer = Literal["m4a", "mp3", "mka", "flac"]
"""Feature-rich containers that reliably support thumbnails."""

RichVideoContainer = Literal["mp4", "mkv"]
"""Feature-rich containers that reliably support thumbnails, subtitles and merging."""

RichAVContainer = RichVideoContainer | RichAudioContainer
"""Feature-rich containers that reliably support thumbnails, subtitles or merging."""
