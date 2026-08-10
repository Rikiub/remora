from remora.models.container import ExtensionType
from remora.models.protocol import Protocol
from remora.models.rank._config import RANK
from remora.models.stream.item import (
    AudioStream,
    MuxedStream,
    Stream,
    StreamType,
    VideoStream,
)


def get_stream_rank(stream: Stream) -> tuple[float, ...]:
    # Get general ranks
    has_video = 0

    video_ext = 0
    audio_ext = 0

    protocol = get_protocol_rank(stream.protocol)

    if isinstance(stream, VideoStream):
        video_ext = get_extension_rank(stream.extension, "video")
        has_video = 1
    if isinstance(stream, AudioStream):
        audio_ext = get_extension_rank(stream.extension, "audio")

    # Calculate total rank
    match stream:
        case MuxedStream():
            return (
                has_video,
                *get_video_rank(stream),
                *get_audio_rank(stream),
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case VideoStream():
            return (
                has_video,
                *get_video_rank(stream),
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case AudioStream():
            return (
                has_video,
                stream.size_bytes or 0,
                *get_audio_rank(stream),
                protocol,
                audio_ext,
            )
        case _:
            raise ValueError("Unable to sort streams. The stream type don't match.")


def get_video_rank(stream: VideoStream) -> tuple[float, ...]:
    """Rank the video part of a stream to compare quality between types."""
    video = stream.video

    return (
        video.resolution.height if video.resolution else 0,
        video.fps or 0,
        get_codec_rank(video.codec, "video"),
    )


def get_audio_rank(stream: AudioStream) -> tuple[float, ...]:
    """Rank the audio part of a stream to compare quality between types."""
    audio = stream.audio

    return (
        audio.channels or 0,
        get_codec_rank(audio.codec, "audio"),
        audio.bitrate or 0,
        audio.sample_rate or 0,
    )


def get_codec_rank(codec: str | None, type: StreamType) -> int:
    rank = RANK["audio_codec"] if type == "audio" else RANK["video_codec"]
    return _rank(codec, rank)


def get_extension_rank(extension: ExtensionType | None, type: StreamType) -> int:
    rank = RANK["audio_extension"] if type == "audio" else RANK["video_extension"]
    return _rank(extension, rank)


def get_protocol_rank(protocol: Protocol | None) -> int:
    return _rank(protocol, RANK["protocol"])


def _rank(value: str | None, rank_list: list[str]) -> int:
    """
    Helper to calculate the rank of a value from a list.
    The list must be sorted from worst to best.
    """

    if not value:
        return -1

    for index, name in enumerate(rank_list):
        if name in value:
            return index

    return -1
