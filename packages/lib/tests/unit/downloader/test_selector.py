from remora._internal.downloader.selector import SelectorContext, StreamSelector
from remora.models.container import CodecInfo
from remora.models.download_options import DownloadOptions
from remora.models.media.item import Media
from remora.models.metadata.size import Resolution
from remora.models.stream.item import (
    AudioInfo,
    AudioStream,
    MuxedStream,
    VideoInfo,
    VideoStream,
)


# Tests
def test_prefers_pair_when_both_better_than_muxed():
    """Prefer merging separate streams when both beat the muxed one."""
    media = make_media(
        muxed_stream(height=720, audio_bitrate=128),
        video_stream(height=1080),
        audio_stream(bitrate=128, codec="opus"),
    )

    result = resolve(media)

    assert not result.muxed
    assert result.video
    assert result.audio


def test_prefers_muxed_when_better_than_pair():
    """Prefer the complete muxed stream when it is better than the pair."""
    media = make_media(
        muxed_stream(height=1080, audio_bitrate=128),
        video_stream(height=720),
        audio_stream(bitrate=48),
    )

    result = resolve(media)

    assert result.muxed
    assert not result.video
    assert not result.audio


def test_prefers_pair_when_muxed_not_strictly_better():
    """The muxed stream must be strictly better on both parts to win."""
    media = make_media(
        muxed_stream(height=1080, audio_bitrate=128),
        video_stream(height=1080),
        audio_stream(bitrate=128),
    )

    result = resolve(media)
    assert not result.muxed
    assert result.video
    assert result.audio


def test_prefers_muxed_when_merge_not_available():
    """Without merging, the complete muxed stream is always preferred."""
    media = make_media(
        muxed_stream(height=720, audio_bitrate=128),
        video_stream(height=1080),
        audio_stream(bitrate=128, codec="opus"),
    )

    result = StreamSelector(
        config=DownloadOptions(),
        merge_available=False,
    ).resolve(media)

    assert result.muxed
    assert not result.video
    assert not result.audio


def test_audio_only_format():
    """Audio format selection still returns only the audio stream."""
    media = make_media(
        muxed_stream(height=1080),
        audio_stream(bitrate=128),
    )
    selector = StreamSelector(DownloadOptions(format_type="audio"))
    result = selector.resolve(media)

    assert not result.muxed
    assert not result.video
    assert result.audio


def test_falls_back_to_pair_without_muxed():
    """Without any muxed stream, the pair is always selected."""
    media = make_media(
        video_stream(height=1080),
        audio_stream(bitrate=128),
    )

    result = resolve(media)

    assert not result.muxed
    assert result.video
    assert result.audio


def test_falls_back_to_muxed_without_separates():
    """A muxed stream is used when no separate video and audio exist."""
    media = make_media(muxed_stream(height=1080))

    result = resolve(media)
    assert result.muxed


def test_extract_best_does_not_mix_stream_types():
    """Each stream type must select from its own candidate list."""
    selector = StreamSelector(DownloadOptions())
    media = make_media(
        muxed_stream(height=1080),
        video_stream(height=720),
        audio_stream(bitrate=128),
    )

    muxed = selector.extract_best(media.streams, MuxedStream)
    video = selector.extract_best(media.streams, VideoStream)
    audio = selector.extract_best(media.streams, AudioStream)

    assert muxed
    assert video
    assert audio


# Helpers
URL = "https://example.com/video"


def resolve(media: Media, **kwargs) -> SelectorContext:
    return StreamSelector(DownloadOptions()).resolve(media, **kwargs)


def make_media(*streams) -> Media:
    return Media(
        extractor="Youtube",
        id="test",
        title="Test",
        url=URL,
        streams=list(streams),
    )


def video_stream(
    height: int,
    id: str = "video",
    codec: str = "h264",
    fps: float | None = None,
) -> VideoStream:
    return VideoStream(
        id=id,
        url=URL,
        protocol="https",
        extension="mp4",
        size_type="unknown",
        video=VideoInfo(
            codec=CodecInfo(original=codec),
            resolution=Resolution(
                width=int(height * 16 / 9),
                height=height,
            ),
            fps=fps,
        ),
    )


def audio_stream(
    bitrate: float | None,
    id: str = "audio",
    codec: str = "aac",
    channels: int = 2,
    sample_rate: float = 44100,
) -> AudioStream:
    return AudioStream(
        id=id,
        url=URL,
        protocol="https",
        extension="m4a",
        size_type="unknown",
        audio=AudioInfo(
            codec=CodecInfo(original=codec),
            bitrate=bitrate,
            channels=channels,
            sample_rate=sample_rate,
        ),
    )


def muxed_stream(
    height: int,
    id: str = "muxed",
    audio_bitrate: float | None = None,
    video_codec: str = "h264",
    audio_codec: str = "aac",
) -> MuxedStream:
    return MuxedStream(
        id=id,
        url=URL,
        protocol="https",
        extension="mp4",
        size_type="unknown",
        video=VideoInfo(
            codec=CodecInfo(original=video_codec),
            resolution=Resolution(
                width=int(height * 16 / 9),
                height=height,
            ),
        ),
        audio=AudioInfo(
            codec=CodecInfo(original=audio_codec),
            bitrate=audio_bitrate,
            channels=2,
            sample_rate=44100,
        ),
    )
