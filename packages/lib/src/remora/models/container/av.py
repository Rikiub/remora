from __future__ import annotations

from typing import Literal, Self

from typing_extensions import override

from remora.models.container._base import GetterEnum


class AVContainer(GetterEnum):
    """Video and audio containers.

    Allows pass a raw extension and determine the container from it.
    """

    # Video and Audio
    AVI = "AVI"
    FLV = "FLV"
    MP4 = "MP4"
    MOV = "MOV"
    MKV = "MKV"
    OGV = "OGV"
    WEBM = "WEBM"
    V3GP = "3GP"
    MPG = "MPG"
    TS = "TS"
    WMV = "WMV"

    # Audio-only
    AIFF = "AIFF"
    FLAC = "FLAC"
    OGG = "OGG"
    MKA = "MKA"
    M4A = "M4A"
    MP3 = "MP3"
    WEBA = "WEBA"
    WAV = "WAV"
    AAC = "AAC"
    APE = "APE"

    @property
    def extension(self) -> str:
        return self.value.lower()

    @property
    def is_audio_only(self) -> bool:
        return self in {
            AVContainer.AIFF,
            AVContainer.FLAC,
            AVContainer.MKA,
            AVContainer.OGG,
            AVContainer.M4A,
            AVContainer.MP3,
            AVContainer.WAV,
            AVContainer.AAC,
            AVContainer.APE,
        }

    @property
    def supports_thumbnails(self) -> bool:
        """Checks if container reliably supports embedded cover art."""
        return self in {
            AVContainer.MKV,
            AVContainer.MKA,
            AVContainer.MP4,
            AVContainer.M4A,
            AVContainer.MOV,
        }

    @property
    def supports_subtitles(self) -> bool:
        """Checks if container reliably supports embedded subtitles."""
        return self in {
            AVContainer.MKV,
            AVContainer.MKA,
            AVContainer.MP4,
            AVContainer.M4A,
            AVContainer.MOV,
            AVContainer.WEBM,
        }

    @override
    @classmethod
    def get(cls, value: str | None) -> Self | None:
        if not value:
            return None

        value = value.lower().lstrip(".").strip()
        target = _ALIAS_MAP.get(value, value)

        for member in cls:
            if member.lower() == target.lower():
                return member
        return None


# Mapping extensions/aliases to canonical Enum values
_ALIAS_MAP: dict[str, str] = {
    alias: canonical
    for canonical, aliases in {
        AVContainer.MP4: (
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
        AVContainer.MOV: ("qt", "quicktime"),
        AVContainer.V3GP: ("3gpp", "3g2", "3gpp2"),
        AVContainer.MKV: ("mk3d",),
        AVContainer.OGG: ("oga", "ogx", "opus", "vorbis", "spx"),
        AVContainer.MPG: ("mpeg", "m2v", "m2p", "mpe", "vob"),
        AVContainer.TS: ("m2ts", "mts"),
        AVContainer.WMV: ("wma", "asf"),
        AVContainer.AIFF: ("aif", "aifc"),
        AVContainer.WAV: ("wave",),
        AVContainer.APE: ("mac",),
        AVContainer.MP3: ("mpeg3", "mpg3", "mp1", "mp2"),
    }.items()
    for alias in aliases
}

# Specializations
# Mostly for autocompletion

VideoContainer = (
    AVContainer
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

AudioContainer = (
    AVContainer
    | Literal[
        "aiff",
        "flac",
        "ogg",
        "opus",
        "weba",
        "mka",
        "m4a",
        "mp3",
        "wav",
        "aac",
        "ape",
    ]
)
"""Common audio-only containers."""

AVContainerLike = VideoContainer | AudioContainer
"""Common video and audio-only containers."""

# Rich specializations
# Recommended safe containers

RichAudioContainer = Literal["m4a", "mp3", "mka", "flac"]
"""Feature-rich containers that reliably support thumbnails."""

RichVideoContainer = Literal["mp4", "mkv"]
"""Feature-rich containers that reliably support thumbnails, subtitles and merging."""

RichAVContainer = RichVideoContainer | RichAudioContainer
"""Feature-rich containers that reliably support thumbnails, subtitles or merging."""
