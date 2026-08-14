from collections.abc import Iterator
from functools import cache

from remora.models.container import AudioExtension, Extension, VideoExtension
from remora.models.protocol import Protocol
from remora.models.rank._config import RANK
from remora.models.stream import (
    AudioInfo,
    AudioStream,
    MuxedStream,
    Stream,
    VideoInfo,
    VideoStream,
)
from remora.models.stream.item import DynamicRange


def get_stream_rank(stream: Stream) -> tuple[float, ...]:
    # Get general ranks
    has_video = 0

    video_ext = 0
    audio_ext = 0

    protocol = get_protocol_rank(stream.protocol)

    if isinstance(stream, VideoStream):
        video_ext = get_extension_rank(stream.extension)
        has_video = 1
    if isinstance(stream, AudioStream):
        audio_ext = get_extension_rank(stream.extension)

    # Calculate total rank
    match stream:
        case MuxedStream():
            return (
                has_video,
                *get_video_rank(stream.video),
                *get_audio_rank(stream.audio),
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case VideoStream():
            return (
                has_video,
                *get_video_rank(stream.video),
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case AudioStream():
            return (
                has_video,
                stream.size_bytes or 0,
                *get_audio_rank(stream.audio),
                protocol,
                audio_ext,
            )


def get_video_rank(video: VideoInfo) -> tuple[float, ...]:
    """Rank the video part of a stream to compare quality between types."""
    return (
        video.resolution.height if video.resolution else 0,
        video.fps or 0,
        get_dynamic_range_rank(video.dynamic_range),
        get_codec_rank(video),
    )


def get_audio_rank(audio: AudioInfo) -> tuple[float, ...]:
    """Rank the audio part of a stream to compare quality between types."""
    return (
        audio.channels or 0,
        get_codec_rank(audio),
        audio.bitrate or 0,
        audio.sample_rate or 0,
    )


def get_protocol_rank(protocol: Protocol) -> int:
    return _rank(protocol, RANK["protocol"])


def get_dynamic_range_rank(value: DynamicRange | str) -> int:
    return _rank(value, RANK["dynamic_range"])


def get_codec_rank(info: VideoInfo | AudioInfo) -> int:
    match info:
        case VideoInfo():
            rank = RANK["video_codec"]
        case AudioInfo():
            rank = RANK["audio_codec"]
    return _rank(info.codec.normalized, rank)


def get_extension_rank(extension: Extension) -> int:
    match extension:
        case VideoExtension():
            rank = RANK["video_extension"]
        case AudioExtension():
            rank = RANK["audio_extension"]
    return _rank(extension, rank)


def _rank(value: str | None, ranks: tuple) -> int:
    """
    Helper to calculate the rank of a value from a list.
    The list must be sorted from worst to best.
    """

    DEFAULT = -1
    if not value:
        return DEFAULT

    # Invert the list for calculate ranks from worst to best
    for index, name in enumerate(_reversed_rank_list(ranks)):
        if name in value:
            return index

    return DEFAULT


@cache
def _reversed_rank_list(ranks: tuple) -> Iterator[str]:
    return reversed(ranks)
