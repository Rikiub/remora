import pytest
from utils import get_ydl_fixture

from remora.models.media.item import Media
from remora.models.metadata.subtitle import SubtitleList


@pytest.fixture(scope="module")
async def subs():
    data = get_ydl_fixture("youtube_video.json")
    media = Media(**data)
    return media.subtitles


async def test_externals(subs: SubtitleList):
    assert len(subs.externals) >= 1


async def test_languages(subs: SubtitleList):
    assert all(key in subs.languages for key in {"en", "es-419"})


class TestFilters:
    async def test_languages(self, subs: SubtitleList):
        results = subs.filter(language="es")
        assert all(s.language.startswith("es") for s in results)

    async def test_extension(self, subs: SubtitleList):
        results = subs.filter(extension="vtt")
        assert all(s.extension == "vtt" for s in results)
