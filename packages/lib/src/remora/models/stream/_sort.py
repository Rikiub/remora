from remora.models.codec.audio import AudioCodec
from remora.models.codec.video import VideoCodec
from remora.models.format.protocol import Protocol
from remora.models.format.type import FormatKind, FormatType
from remora.models.stream.item import AudioStream, MuxedStream, Stream, VideoStream


def get_stream_rank(stream: Stream) -> tuple[float, ...]:
    protocol = get_protocol_rank(stream.protocol)

    match stream:
        case MuxedStream():
            vcodec = get_codec_rank(stream.video_codec, FormatKind.VIDEO)
            acodec = get_codec_rank(stream.audio_codec, FormatKind.AUDIO)
            is_video = 1

            return (
                is_video,
                stream.resolution.height if stream.resolution else 0,
                stream.fps or 0,
                vcodec,
                acodec,
                stream.size_bytes or 0,
                protocol,
            )
        case VideoStream():
            vcodec = get_codec_rank(stream.codec, FormatKind.VIDEO)
            is_video = 1

            return (
                is_video,
                stream.resolution.height if stream.resolution else 0,
                stream.fps or 0,
                vcodec,
                stream.size_bytes or 0,
                protocol,
            )
        case AudioStream():
            acodec = get_codec_rank(stream.codec, FormatKind.AUDIO)
            is_video = 0

            return (
                is_video,
                stream.size_bytes or 0,
                acodec,
                stream.bitrate or 0,
                protocol,
            )
        case _:
            raise ValueError("Unable to sort streams. The stream type don't match.")


_VIDEO_LIST = VideoCodec.by_best()[::-1]
_AUDIO_LIST = AudioCodec.by_best()[::-1]
_PROTOCOL_LIST = Protocol.by_best()[::-1]


def get_codec_rank(codec: str | None, type: FormatType) -> int:
    if not codec:
        return -1

    priority: list[str] = (
        _AUDIO_LIST if type == FormatKind.AUDIO else _VIDEO_LIST  # type: ignore
    )

    try:
        # Higher index = Better quality
        return priority.index(codec)
    except ValueError:
        return -1  # Unknown codec is ranked lowest


def get_protocol_rank(protocol: Protocol | None) -> int:
    if not protocol:
        return -1

    for index, name in enumerate(_PROTOCOL_LIST):
        if name in protocol:
            return index

    return -1
