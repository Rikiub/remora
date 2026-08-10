from typing import Literal

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
    "AudioExtension",
    "AudioExtensionType",
    "ExtensionType",
    "FormatType",
    "SafeAudioExtensionStr",
    "SafeVideoExtensionStr",
    "VideoExtension",
    "VideoExtensionType",
    "get_extension",
]
