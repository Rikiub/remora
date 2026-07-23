from remora.models.format.extension import ExtensionType
from remora.models.protocol import Protocol
from remora.models.stream._filters.config import RANK
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

    video_codec = 0
    video_ext = 0

    audio_codec = 0
    audio_ext = 0

    protocol = get_protocol_rank(stream.protocol)

    if isinstance(stream, VideoStream):
        video_codec = get_codec_rank(stream.video.codec, "video")
        video_ext = get_extension_rank(stream.extension, "video")
        has_video = 1
    if isinstance(stream, AudioStream):
        audio_codec = get_codec_rank(stream.audio.codec, "audio")
        audio_ext = get_extension_rank(stream.extension, "audio")

    # Calculate total rank
    match stream:
        case MuxedStream():
            video = stream.video
            audio = stream.audio

            return (
                has_video,
                video.resolution.height if video.resolution else 0,
                video.fps or 0,
                video_codec,
                audio.channels or 0,
                audio_codec,
                audio.sample_rate or 0,
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case VideoStream():
            video = stream.video

            return (
                has_video,
                video.resolution.height if video.resolution else 0,
                video.fps or 0,
                video_codec,
                stream.size_bytes or 0,
                protocol,
                video_ext,
            )
        case AudioStream():
            audio = stream.audio

            return (
                has_video,
                stream.size_bytes or 0,
                audio.channels or 0,
                audio_codec,
                audio.bitrate or 0,
                audio.sample_rate or 0,
                protocol,
                audio_ext,
            )
        case _:
            raise ValueError("Unable to sort streams. The stream type don't match.")


def get_codec_rank(codec: str | None, type: StreamType) -> int:
    rank = RANK["audio_codec"] if type == "audio" else RANK["video_codec"]
    return _rank(codec, rank)


def get_extension_rank(extension: ExtensionType | None, type: StreamType) -> int:
    rank = RANK["audio_extension"] if type == "audio" else RANK["video_extension"]
    return _rank(extension, rank)


def get_protocol_rank(protocol: Protocol | None) -> int:
    return _rank(protocol, RANK["protocol"])


def _rank(value: str | None, rank_list: list[str]):
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
