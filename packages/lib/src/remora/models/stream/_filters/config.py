from remora.models.protocol import Protocol

# Ranks sorted from best to worst
RANK: dict[str, list[str]] = {
    "protocol": [
        Protocol.HTTPS,
        Protocol.FTPS,
        Protocol.HTTP,
        Protocol.FTP,
        Protocol.M3U8_NATIVE,
        Protocol.M3U8,
        Protocol.HTTP_DASH_SEGMENTS,
        Protocol.WEBSOCKET_FRAG,
        Protocol.MMS,
        Protocol.RTSP,
        Protocol.F4F,
        Protocol.F4M,
    ],
    "video_codec": [
        "av01",
        "vp9.2",
        "vp9",
        "hevc",
        "h265",
        "vp8",
        "avc",
        "h264",
        "mp4v",
        "h263",
        "theora",
    ],
    "audio_codec": [
        "aiff",
        "wav",
        "alac",
        "flac",
        "opus",
        "vorbis",
        "mp4a",
        "aac",
        "mp3",
        "ac4",
        "dts",
        "eac3",
        "ac3",
    ],
    "video_extension": ["mp4", "mov", "webm", "flv"],
    "audio_extension": ["m4a", "aac", "mp3", "ogg", "opus", "webm", "webam"],
}

# Invert lists for calculate ranks from worst to best
for key, values in RANK.items():
    RANK[key] = list(reversed(values))
