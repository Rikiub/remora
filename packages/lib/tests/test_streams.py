from pathlib import Path

import pytest

from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, VideoStream
from remora.models.stream.list import StreamList


@pytest.fixture(scope="module")
async def streams(root_path: Path):
    path = root_path / "resources" / "youtube-video.json"
    media = Media.model_validate_json(path.read_bytes())
    return media.streams


# StreamList Tests
async def test_video_type(streams: StreamList):
    fmt = streams.only_video()
    assert all(isinstance(f, VideoStream) for f in fmt)


async def test_audio_type(streams: StreamList):
    fmt = streams.only_audio()
    assert all(isinstance(f, AudioStream) for f in fmt)


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
