from enum import StrEnum


class Codec(StrEnum):
    @classmethod
    def __missing__(cls, value):
        """Lowercase and take everything before the first dot/dash

        Example: "avc1.640028" -> "avc1"
        Example: "mp4a.40.2"   -> "mp4a"
        """

        if not isinstance(value, str):
            return None

        value = str(value).lower().split(".")[0].split("-")[0].strip()

        for member in cls:
            if member.value.startswith(value):
                return member

        return None


class CodecFamily(Codec):
    # Video

    ## VP
    VP9 = "vp9"
    VP8 = "vp8"
    AV1 = "av1"

    ## H.2xx/HEVC
    H265 = "h265"
    H264 = "h264"
    H263 = "h263"

    ## MPEG
    MPEG4 = "mpeg4"
    MPEG2 = "mpeg2"

    ## Others
    THEORA = "theora"
    DOVI = "dovi"

    # Audio

    ## Lossless
    AIFF = "aiff"
    WAV = "wav"
    FLAC = "flac"

    ## MP3
    MP3 = "mp3"

    ## AAC
    AAC = "aac"
    AAC_MPEG2 = "acc_mpeg2"
    AAC_LC = "aac_lc"
    ACC_HE = "acc_he"
    AAC_HE_V2 = "aac_he_v2"
    AAC_XHE = "aac_xhe"

    ## Vorbis
    OPUS = "opus"
    VORBIS = "vorbis"

    ## Dolby
    AC4 = "ac4"
    AC3 = "ac3"
    EAC3 = "eac3"

    ## DTS
    DTS = "dts"

    ## Others
    ALAC = "alac"

    # Default
    UNKNOWN = "unknown"
