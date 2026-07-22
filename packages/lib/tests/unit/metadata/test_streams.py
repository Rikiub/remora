import pytest

from remora._internal.extractor import MediaExtractor
from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, MuxedStream, VideoStream
from remora.models.stream.list import StreamList


@pytest.fixture
async def streams(mock_extractor) -> StreamList:
    mock_extractor("youtube/video.json")

    data = await MediaExtractor().extract("")
    assert isinstance(data, Media)

    assert len(data.streams) > 0
    return data.streams


# Filters: Video and Audio
@pytest.mark.parametrize(
    "method, expected_class",
    [
        ("muxed", MuxedStream),
        ("videos", (VideoStream, MuxedStream)),
        ("audios", (AudioStream, MuxedStream)),
    ],
)
async def test_stream_type_filters(streams: StreamList, method, expected_class):
    filtered = getattr(streams, method)()
    assert len(filtered) > 0, f"No streams returned for .{method}()"
    assert all(isinstance(s, expected_class) for s in filtered)


@pytest.mark.parametrize(
    "method, expected_class",
    [
        ("video_only", VideoStream),
        ("audio_only", AudioStream),
    ],
)
async def test_stream_strict_type_filters(streams: StreamList, method, expected_class):
    filtered = getattr(streams, method)()
    assert len(filtered) > 0, f"No streams returned for .{method}()"
    assert all(type(s) is expected_class for s in filtered)


# Filters: General
@pytest.mark.parametrize(
    "filter_kwargs, attr_name, expected_value",
    [
        ({"extension": "mp4"}, "extension", "mp4"),
        ({"quality": 720}, "quality", 720),
        ({"protocol": "https"}, "protocol", "https"),
    ],
)
async def test_generic_filters(
    streams: StreamList, filter_kwargs, attr_name, expected_value
):
    filtered = streams.filter(**filter_kwargs)
    assert len(filtered) > 0, f"Filter {filter_kwargs} yielded no results"
    assert all(getattr(s, attr_name) == expected_value for s in filtered)


async def test_filter_video_codec(streams: StreamList):
    codec = "vp9"
    filtered = streams.filter(video_codec=codec)
    assert len(filtered) > 0
    assert all(
        isinstance(s, VideoStream) and s.video.codec.startswith(codec) for s in filtered
    )


async def test_filter_audio_codec(streams: StreamList):
    codec = "opus"
    filtered = streams.filter(audio_codec=codec)
    assert len(filtered) > 0
    assert all(
        isinstance(s, AudioStream) and s.audio.codec.startswith(codec) for s in filtered
    )


# Getters
async def test_closest_quality(streams: StreamList):
    stream = streams.get_closest_quality(600)
    assert stream.quality == 720


async def test_get_by_id(streams: StreamList):
    stream_id = "137"
    stream = streams.get_by_id(stream_id)
    assert stream.id == stream_id


async def test_get_by_id_raises(streams: StreamList):
    with pytest.raises(KeyError):
        stream_id = "-1"
        streams.get_by_id(stream_id)
