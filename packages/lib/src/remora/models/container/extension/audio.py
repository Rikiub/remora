from enum import StrEnum
from typing import Literal

from typing_extensions import override

from remora.models.container.extension._base import BaseExtension


class AudioExtension(BaseExtension, StrEnum):
    # Common
    AIFF = "aiff"
    ALAC = "alac"
    FLAC = "flac"
    M4A = "m4a"
    MKA = "mka"
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"
    WAV = "wav"

    # Extra
    AAC = "aac"
    APE = "ape"
    ASF = "asf"
    F4A = "f4a"
    F4B = "f4b"
    M4B = "m4b"
    M4R = "m4r"
    OGA = "oga"
    OGX = "ogx"
    SPX = "spx"
    VORBIS = "vorbis"
    WMA = "wma"
    WEBM = "webm"
    WEBA = "weba"

    @property
    @override
    def supports_thumbnails(self) -> bool:
        """Checks if container reliably supports embedded cover art."""
        return self in {
            AudioExtension.M4A,
            AudioExtension.MP3,
            AudioExtension.MKA,
            AudioExtension.OGG,
            AudioExtension.OPUS,
            AudioExtension.FLAC,
        }


_AudioExtensionLiteral = Literal[
    # Common
    "aiff",
    "alac",
    "flac",
    "m4a",
    "mka",
    "mp3",
    "ogg",
    "opus",
    "wav",
    # Extra
    "aac",
    "ape",
    "asf",
    "f4a",
    "f4b",
    "m4b",
    "m4r",
    "oga",
    "ogx",
    "spx",
    "vorbis",
    "wma",
    "webm",
    "weba",
]
AudioExtensionLike = AudioExtension | _AudioExtensionLiteral
SafeAudioExtension = Literal["m4a", "mp3", "mka", "flac"]
