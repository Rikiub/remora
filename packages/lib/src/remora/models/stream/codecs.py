from remora.types import FORMAT_TYPE

VIDEO_CODEC_RANK = {
    "vp9": 10,
    "av01": 8,
    "vp8": 7,
    "h265": 6,
    "hevc": 6,
    "h264": 5,
    "avc": 5,
    "mp4v": 4,
}
AUDIO_CODEC_RANK = {
    "opus": 10,
    "vorbis": 9,
    "aac": 8,
    "mp4a": 8,
    "mp3": 5,
    "ac-3": 4,
}


def get_codec_rank(
    codec: str | None,
    type: FORMAT_TYPE,
) -> int:
    if not codec:
        return 0

    dict = VIDEO_CODEC_RANK if type == "video" else AUDIO_CODEC_RANK
    codec = codec.lower()

    for key, rank in dict.items():
        if key in codec:
            return rank

    return 1
