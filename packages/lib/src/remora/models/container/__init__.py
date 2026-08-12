from typing import Literal

from remora.models.container.codec import (
    AudioCodecFamily,
    CodecFamilyType,
    CodecInfo,
    VideoCodecFamily,
)
from remora.models.container.extension import (
    AudioExtension,
    AudioExtensionType,
    ExtensionType,
    SafeAudioExtensionStr,
    SafeVideoExtensionStr,
    VideoExtension,
    VideoExtensionType,
    get_extension,
)

FormatType = Literal["video", "audio"]

__all__ = [
    "AudioCodecFamily",
    "AudioCodecFamilyStr",
    "AudioExtension",
    "AudioExtensionType",
    "CodecFamilyType",
    "CodecInfo",
    "ExtensionType",
    "FormatType",
    "SafeAudioExtensionStr",
    "SafeVideoExtensionStr",
    "VideoCodecFamily",
    "VideoCodecFamilyStr",
    "VideoExtension",
    "VideoExtensionType",
    "get_extension",
]
