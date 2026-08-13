from typing import Literal

from remora.models.container.codec import Codec, CodecFamily
from remora.models.container.codec.audio import AudioCodec, AudioCodecFamily
from remora.models.container.codec.info import CodecInfo
from remora.models.container.codec.video import VideoCodec, VideoCodecFamily
from remora.models.container.extension import (
    AudioExtension,
    AudioExtensionLike,
    Extension,
    ExtensionLike,
    SafeAudioExtension,
    SafeExtension,
    SafeVideoExtension,
    VideoExtension,
    VideoExtensionLike,
    get_extension,
)

ContainerFormat = Literal["video", "audio"]

__all__ = [
    "AudioCodec",
    "AudioCodecFamily",
    "AudioExtension",
    "AudioExtensionLike",
    "Codec",
    "CodecFamily",
    "CodecInfo",
    "ContainerFormat",
    "Extension",
    "ExtensionLike",
    "SafeAudioExtension",
    "SafeExtension",
    "SafeVideoExtension",
    "VideoCodec",
    "VideoCodecFamily",
    "VideoExtension",
    "VideoExtensionLike",
    "get_extension",
]
