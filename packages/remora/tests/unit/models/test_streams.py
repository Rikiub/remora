from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pytest

from remora.models.container import CodecInfo
from remora.models.metadata.size import Resolution
from remora.models.stream import Stream
from remora.models.stream.item import (
    AudioInfo,
    AudioStream,
    MuxedStream,
    VideoInfo,
    VideoStream,
)
from remora.models.stream.list import Streams

URL = "https://example.com/video"


@pytest.fixture
def streams() -> Streams:
    """List of streams for testing."""

    return Streams(
        [
            # Covers: muxed, find_by_id(id="2")
            # Covers: quality=720, protocol="https", container="mp4"
            MuxedStream(
                id="2",
                url=URL,
                protocol="https",
                language="en",
                container="mp4",
                size_type="estimated",
                size_bytes=11832459,
                video=VideoInfo(
                    codec=CodecInfo(original="avc1.42001E"),
                    resolution=Resolution(width=1280, height=720),  # Gives quality=720
                    bitrate=444.226,
                    fps=25,
                ),
                audio=AudioInfo(
                    codec=CodecInfo(original="mp4a.40.2"),
                    bitrate=128.0,
                    channels=2,
                    sample_rate=44100,
                ),
            ),
            # Covers: videos, video_only, vp9 codec filter
            VideoStream(
                id="1",
                url=URL,
                protocol="m3u8",
                container="webm",
                video=VideoInfo(
                    codec=CodecInfo(original="vp9"),
                    resolution=Resolution(width=1920, height=1080),
                ),
            ),
            # Covers: audios, audio_only, opus codec filter
            AudioStream(
                id="3",
                url=URL,
                protocol="https",
                container="webm",
                language="es-419",
                audio=AudioInfo(
                    codec=CodecInfo(original="opus"),
                    bitrate=160.0,
                ),
            ),
            # Covers: Extra audio stream for robustness
            AudioStream(
                id="4",
                url=URL,
                protocol="m3u8",
                container="m4a",
                language=None,
                audio=AudioInfo(
                    codec=CodecInfo(original="mp4a.40.5"),
                    bitrate=64.0,
                ),
            ),
        ]
    )


# Filters: Video and Audio
@dataclass
class Case:
    name: str
    filter_streams: Callable[[Streams], Sequence[Stream]]
    expected_class: type | tuple[type, ...]


CASES = [
    Case("muxed", lambda s: s.muxed(), MuxedStream),
    Case("videos", lambda s: s.videos(), (VideoStream, MuxedStream)),
    Case("audios", lambda s: s.audios(), (AudioStream, MuxedStream)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_stream_type_filters(streams: Streams, case: Case):
    filtered = case.filter_streams(streams)

    assert len(filtered) > 0, f"No streams returned for {case.name}"
    assert all(isinstance(s, case.expected_class) for s in filtered)


# Filters: Video-only and Audio-only
@dataclass
class Case:
    name: str
    filter_streams: Callable[[Streams], Sequence[Stream]]
    expected_class: type


CASES = [
    Case("video_only", lambda s: s.video_only(), VideoStream),
    Case("audio_only", lambda s: s.audio_only(), AudioStream),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_stream_strict_type_filters(streams: Streams, case: Case):
    filtered = case.filter_streams(streams)
    assert len(filtered) > 0, f"No streams returned for {case.name}()"
    assert all(type(s) is case.expected_class for s in filtered)


# Filters: General
@pytest.mark.parametrize(
    "attribute, filter_value",
    [
        ("quality", 720),
        ("protocol", "HTTPS"),
        ("container", "WEBM"),
    ],
)
def test_filter_general(streams: Streams, attribute, filter_value):
    filters = {attribute: filter_value}
    filtered = streams.filter(**filters)

    assert len(filtered) > 0, f"Filter {filters} yielded no results"
    assert all(getattr(s, attribute) == filter_value for s in filtered)


def test_filter_language(streams: Streams):
    """
    Test filter of partial languages keys.
    Should be able of found audio streams with `es-419` like keys.
    """

    language = "es"
    filtered = streams.filter(language=language)

    assert len(filtered) > 0
    assert all(
        isinstance(s, AudioStream) and s.language and s.language.startswith(language)
        for s in filtered
    )


def test_filter_video_codec_family(streams: Streams):
    """Test filter of partial video codec strings."""

    codec = "vp9"
    filtered = streams.filter(video_codec=codec)

    assert len(filtered) > 0
    assert all(
        isinstance(s, VideoStream) and (c := s.video.codec) and c.family == "VP9"
        for s in filtered
    )


def test_filter_audio_codec_family(streams: Streams):
    """Test filter of partial audio codec strings."""

    codec = "opus"
    filtered = streams.filter(audio_codec=codec)

    assert len(filtered) > 0
    assert all(
        isinstance(s, AudioStream) and (c := s.audio.codec) and c.family == "Opus"
        for s in filtered
    )


# Sorter
def test_sorted_by_best(streams: Streams):
    streams = streams.sorted_by("best")

    match_ids = ["1", "2", "3", "4"]  # Must match with the fixture
    streams_ids = [s.id for s in streams]
    assert len(streams_ids) > 0

    for index, _ in enumerate(streams_ids):
        assert match_ids[index] == streams_ids[index]


# Getters
def test_closest_quality(streams: Streams):
    stream = streams.get_closest_quality(600)
    assert stream.quality == 720


def test_get_by_id(streams: Streams):
    ID = "1"
    stream = streams.get_by_id(ID)
    assert stream.id == ID


def test_missing_get_by_id(streams: Streams):
    with pytest.raises(KeyError):
        stream_id = "-1"
        streams.get_by_id(stream_id)
