from __future__ import annotations

from typing import Literal

from typing_extensions import Self, override

from remora.models.container._base import GetterEnum
from remora.models.container.codec.audio import AudioCodecFamily


class AVContainer(GetterEnum):
    """Video and audio containers.

    Allows pass a raw extension and determine the container from it.
    """

    # Video and Audio
    AVI = "AVI"
    FLV = "FLV"
    MP4 = "MP4"
    MOV = "MOV"
    V3GP = "3GP"
    MKV = "MKV"
    WEBM = "WEBM"
    OGG = "OGG"
    MPG = "MPG"
    TS = "TS"
    WMV = "WMV"

    # Audio-only
    AIFF = "AIFF"
    FLAC = "FLAC"
    MP3 = "MP3"
    WAV = "WAV"
    AAC = "AAC"
    APE = "APE"

    def get_extension(
        self,
        has_video: bool = True,
        audio_codec: AudioCodecFamily | str | None = None,
    ) -> str:
        """
        Dynamically calculates the correct file extension based on the container
        and the streams it holds.

        Args:
            has_video: `True` if a video stream is present.
            audio_codec: Pass the string or `AudioCodecFamily` enum.
        """
        ac = AudioCodecFamily(audio_codec) if audio_codec else None

        match self:
            case AVContainer.MP4:
                if not has_video:
                    return "m4a"
                return "mp4"
            case AVContainer.MKV:
                if not has_video:
                    return "mka"
                return "mkv"
            case AVContainer.OGG:
                if not has_video and ac in (
                    AudioCodecFamily.OPUS,
                    AudioCodecFamily.VORBIS,
                    AudioCodecFamily.SPX,
                ):
                    return ac if ac == AudioCodecFamily.OPUS else "ogg"
                return "ogv" if has_video else "ogg"
            case AVContainer.TS:
                return "m2ts" if has_video else "ts"

        # For all other formats
        return self.value

    @property
    def is_audio_only(self) -> bool:
        return self in {
            AVContainer.AIFF,
            AVContainer.FLAC,
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
            AVContainer.MP4,
            AVContainer.MOV,
        }

    @property
    def supports_subtitles(self) -> bool:
        """Checks if container reliably supports embedded subtitles."""
        return self in {
            AVContainer.MKV,
            AVContainer.MP4,
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
_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    AVContainer.MP4: (
        # Apple extensions
        "m4v",
        "m4a",
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
    AVContainer.MKV: ("mka", "mk3d"),
    AVContainer.OGG: ("oga", "ogv", "ogx", "opus", "vorbis", "spx"),
    AVContainer.MPG: ("mpeg", "m2v", "m2p", "mpe", "vob"),
    AVContainer.TS: ("m2ts", "mts"),
    AVContainer.WMV: ("wma", "asf"),
    AVContainer.AIFF: ("aif", "aifc"),
    AVContainer.WAV: ("wave",),
    AVContainer.APE: ("mac",),
    AVContainer.MP3: ("mpeg3", "mpg3", "mp1", "mp2"),
}
# Flatten the groups dynamically into an exact-match lookup map
_ALIAS_MAP: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _ALIAS_GROUPS.items()
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
