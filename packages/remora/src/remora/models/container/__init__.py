from typing import Literal

from .av import (
    AudioContainer,
    AudioContainerLike,
    AVContainer,
    AVContainerLike,
    RichAudioContainer,
    RichAVContainer,
    RichVideoContainer,
    VideoContainer,
    VideoContainerLike,
    get_container,
)
from .codec.audio import AudioCodec, AudioCodecFamily
from .codec.info import CodecInfo
from .codec.types import Codec, CodecFamily
from .codec.video import VideoCodec, VideoCodecFamily

AVContainerFormat = Literal["video", "audio"]

__all__ = [
    "AVContainer",
    "AVContainerFormat",
    "AVContainerLike",
    "AudioCodec",
    "AudioCodecFamily",
    "AudioContainer",
    "AudioContainerLike",
    "Codec",
    "CodecFamily",
    "CodecInfo",
    "RichAVContainer",
    "RichAudioContainer",
    "RichVideoContainer",
    "VideoCodec",
    "VideoCodecFamily",
    "VideoContainer",
    "VideoContainerLike",
    "get_container",
]
