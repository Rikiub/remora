from typing import Literal

from remora.models.container.codec import Codec, CodecFamily
from remora.models.container.codec.audio import AudioCodec, AudioCodecFamily
from remora.models.container.codec.info import CodecInfo
from remora.models.container.codec.video import VideoCodec, VideoCodecFamily
from remora.models.container.extension import (
    AudioContainer,
    AudioContainerLike,
    SafeAudioContainer,
    SafeContainer,
    SafeVideoContainer,
    StreamContainer,
    StreamContainerLike,
    VideoContainer,
    VideoContainerLike,
    get_stream_container,
)

ContainerFormat = Literal["video", "audio"]

__all__ = [
    "AudioCodec",
    "AudioCodecFamily",
    "AudioContainer",
    "AudioContainerLike",
    "Codec",
    "CodecFamily",
    "CodecInfo",
    "ContainerFormat",
    "SafeAudioContainer",
    "SafeContainer",
    "SafeVideoContainer",
    "StreamContainer",
    "StreamContainerLike",
    "VideoCodec",
    "VideoCodecFamily",
    "VideoContainer",
    "VideoContainerLike",
    "get_stream_container",
]
