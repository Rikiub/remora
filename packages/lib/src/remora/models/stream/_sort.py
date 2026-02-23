from remora._internal.types.base import ExtensionType, ExtensionTypeLike
from remora.models.stream.item import AudioStream, Stream, VideoStream

VIDEO_PRIORITY = [
    "theora",
    "h263",
    "mp4v",
    "h264",
    "avc",
    "vp8",
    "h265",
    "hevc",
    "vp9",
    "vp9.2",
    "av01",
]
AUDIO_PRIORITY = [
    "ac3",
    "eac3",
    "dts",
    "ac4",
    "mp3",
    "aac",
    "mp4a",
    "vorbis",
    "opus",
    "flac",
    "alac",
    "wav",
    "aiff",
]
PROTOCOL_PRIORITY = [
    "f4m",
    "f4f",
    "rtsp",
    "mms",
    "websocket_frag",
    "http_dash_segments",
    "m3u8",
    "m3u8_native",
    "ftp",
    "http",
    "ftps",
    "https",
]


def normalize_codec(codec: str) -> str:
    """Lowercase and take everything before the first dot/dash

    Example: "avc1.640028" -> "avc1"
    Example: "mp4a.40.2"   -> "mp4a"
    """
    return codec.lower().split(".")[0].split("-")[0].strip()


def get_codec_rank(codec: str | None, type: ExtensionTypeLike) -> int:
    if not codec:
        return -1

    priority = AUDIO_PRIORITY if type == ExtensionType.AUDIO else VIDEO_PRIORITY
    codec = normalize_codec(codec)

    try:
        # Higher index = Better quality
        return priority.index(codec)
    except ValueError:
        return -1  # Unknown codec is ranked lowest


def get_protocol_rank(protocol: str | None) -> int:
    if not protocol:
        return -1

    protocol = protocol.lower()

    for index, name in enumerate(PROTOCOL_PRIORITY):
        if name in protocol:
            return index

    return -1


def stream_sort(stream: Stream):
    protocol = get_protocol_rank(stream.protocol)

    if isinstance(stream, VideoStream):
        is_video = 1
        vcodec = get_codec_rank(stream.video_codec, ExtensionType.VIDEO)
        acodec = get_codec_rank(stream.audio_codec, ExtensionType.AUDIO)

        return (
            is_video,
            stream.height or 0,
            stream.fps or 0,
            vcodec,
            acodec,
            stream.size_bytes or 0,
            protocol,
        )

    elif isinstance(stream, AudioStream):
        is_video = 0
        acodec = get_codec_rank(stream.audio_codec, ExtensionType.AUDIO)

        return (
            is_video,
            stream.size_bytes or 0,
            acodec,
            stream.bitrate,
            protocol,
        )
