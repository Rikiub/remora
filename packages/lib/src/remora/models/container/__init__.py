from typing import Literal

from remora.models.container.av import (
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
from remora.models.container.codec.audio import AudioCodec, AudioCodecFamily
from remora.models.container.codec.info import CodecInfo
from remora.models.container.codec.types import Codec, CodecFamily
from remora.models.container.codec.video import VideoCodec, VideoCodecFamily

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
