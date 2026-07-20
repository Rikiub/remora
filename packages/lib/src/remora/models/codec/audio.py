from __future__ import annotations

from remora.models.codec._base import Codec


class AudioCodec(Codec):
    AIFF = "aiff"
    WAV = "wav"
    FLAC = "flac"

    MP3 = "mp3"
    MP4A = "mp4a"

    AAC = "aac"
    ALAC = "alac"

    OPUS = "opus"
    VORBIS = "vorbis"

    AC4 = "ac4"
    AC3 = "ac3"
    EAC3 = "eac3"
    DTS = "dts"

    @classmethod
    def by_best(cls) -> list[AudioCodec]:
        return [
            AudioCodec.AIFF,
            AudioCodec.WAV,
            AudioCodec.ALAC,
            AudioCodec.FLAC,
            AudioCodec.OPUS,
            AudioCodec.VORBIS,
            AudioCodec.MP4A,
            AudioCodec.AAC,
            AudioCodec.MP3,
            AudioCodec.AC4,
            AudioCodec.DTS,
            AudioCodec.EAC3,
            AudioCodec.AC3,
        ]
