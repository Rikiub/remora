from pathlib import Path

import pytest
from remora import AudioFormat, MediaDownloader, VideoFormat
from remora.extractor import MediaExtractor
from remora.models.format.list import FormatList

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


def test_single(tmp_path: Path):
    result = MediaExtractor().extract_url(URL)

    assert result.type == "media"

    if result.type == "media":
        downloader = MediaDownloader("audio", quality=1, output=tmp_path)
        path = downloader.download(result)

        assert path.is_file()


def test_list(tmp_path: Path):
    result = MediaExtractor().extract_url(PLAYLIST)

    assert result.type == "playlist"

    if result.type == "playlist":
        downloader = MediaDownloader("audio", quality=1, output=tmp_path)
        paths = downloader.download_all(result)

        assert all(item for item in paths if item.is_file())


@pytest.fixture(scope="session")
def formats():
    result = MediaExtractor().extract_url(URL)
    assert result.type == "media"
    assert len(result.formats) >= 1
    return result.formats


class TestFormatsFilter:
    def test_video_type(self, formats: FormatList):
        fmt = formats.only_video()
        assert all(isinstance(f, VideoFormat) for f in fmt)

    def test_audio_type(self, formats: FormatList):
        fmt = formats.only_audio()
        assert all(isinstance(f, AudioFormat) for f in fmt)

    def test_closest_quality(self, formats: FormatList):
        fmt = formats.get_closest_quality(600)
        assert fmt.quality == 720

    def test_filter(self, formats: FormatList):
        fmt = formats.filter(quality=720)
        assert all(f.quality == 720 for f in fmt)

    def test_get_by_id(self, formats: FormatList):
        ID = "137"
        fmt = formats.get_by_id(ID)
        assert fmt.id == ID
