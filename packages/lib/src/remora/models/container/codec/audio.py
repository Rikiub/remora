from __future__ import annotations

import re
from typing import Literal

from typing_extensions import override

from remora.models.container._base import GetterEnum


class AudioCodecFamily(GetterEnum):
    # Common
    PCM = "PCM"  # Combines WAV and AIFF
    ALAC = "ALAC"  # Apple Lossless
    FLAC = "FLAC"
    OPUS = "Opus"
    VORBIS = "Vorbis"
    AAC = "AAC"
    MP3 = "MP3"

    # Extra
    AC4 = "AC-4"  # Dolby Digital
    AC3 = "AC-3"  # Dolby Digital Plus
    EAC3 = "E-AC-3"  # Dolby AC-4
    SPX = "SPX"
    DTS = "DTS"

    @override
    @classmethod
    def get(cls, value: str | None) -> AudioCodecFamily | None:
        if not value:
            return None
        value = value.lower().strip()

        codec = {member: member.value.lower() for member in cls}
        codec = codec | {
            cls.PCM: r"wav|aiff",
            cls.VORBIS: r"vorbis|ogg",
            cls.AAC: r"mp?4a?|aac",
            cls.AC4: r"ac-?4",
            cls.AC3: r"ac-?3",
            cls.EAC3: r"e-?a?c-?3",
        }

        for enum, regex in codec.items():
            if re.match(regex, value):
                return enum
        return None


AudioCodec = Literal[
    # Common
    "aac",
    "mp3",
    "opus",
    "vorbis",
    "flac",
    "alac",
    "pcm",
    # Extra
    "ac4",
    "ac3",
    "eac3",
    "dts",
]
