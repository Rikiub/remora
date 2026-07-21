import pytest
from utils import get_ydl_fixture

from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, VideoStream
from remora.models.stream.list import StreamList


@pytest.fixture(scope="module")
async def streams():
    data = get_ydl_fixture("youtube_video.json")
    media = Media(**data)
    return media.streams


# StreamList Tests
async def test_video_type(streams: StreamList):
    fmt = streams.only_video()
    assert all(type(f) is VideoStream for f in fmt)


async def test_audio_type(streams: StreamList):
    fmt = streams.only_audio()
    assert all(type(f) is AudioStream for f in fmt)


async def test_closest_quality(streams: StreamList):
    fmt = streams.get_closest_quality(600)
    assert fmt.quality == 720


async def test_filter(streams: StreamList):
    fmt = streams.filter(quality=720)
    assert all(f.quality == 720 for f in fmt)


async def test_get_by_id(streams: StreamList):
    ID = "137"
    fmt = streams.get_by_id(ID)
    assert fmt.id == ID
