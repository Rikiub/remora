from pathlib import Path

import pytest

from remora import AudioStream, DownloadOptions, MediaExtractor, RemoraAPI, VideoStream
from remora.models.stream.list import StreamList

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


async def test_single(tmp_path: Path):
    api = RemoraAPI(
        download_config=DownloadOptions(format="audio", quality=1, template=tmp_path),
        extractor=MediaExtractor(use_cache=False),
    )

    async for event in api.download(URL):
        if event.status == "finished":
            assert event.filepath.is_file()


async def test_list(tmp_path: Path):
    api = RemoraAPI(
        download_config=DownloadOptions(format="audio", quality=1, template=tmp_path),
        extractor=MediaExtractor(use_cache=False),
    )

    async for event in api.download_batch(PLAYLIST):
        if event.type == "media" and event.status == "finished":
            assert event.filepath.is_file()


@pytest.fixture(scope="session")
async def streams():
    result = await MediaExtractor().extract(URL)
    assert result.type == "media"
    assert len(result.streams) >= 1
    return result.streams


class TestStreamList:
    async def test_video_type(self, streams: StreamList):
        fmt = streams.only_video()
        assert all(isinstance(f, VideoStream) for f in fmt)

    async def test_audio_type(self, streams: StreamList):
        fmt = streams.only_audio()
        assert all(isinstance(f, AudioStream) for f in fmt)

    async def test_closest_quality(self, streams: StreamList):
        fmt = streams.get_closest_quality(600)
        assert fmt.quality == 720

    async def test_filter(self, streams: StreamList):
        fmt = streams.filter(quality=720)
        assert all(f.quality == 720 for f in fmt)

    async def test_get_by_id(self, streams: StreamList):
        ID = "137"
        fmt = streams.get_by_id(ID)
        assert fmt.id == ID
