import pytest

from remora.models.media.item import Media
from remora.models.metadata.subtitle import SubtitleList


@pytest.fixture
def subs(ydl_data):
    data = ydl_data("youtube/video.json")
    data = Media(**data)

    assert len(data.subtitles) > 1
    return data.subtitles


# Filters: Type
async def test_externals(subs: SubtitleList):
    assert len(subs.externals) >= 1


async def test_languages(subs: SubtitleList):
    assert all(key in subs.languages for key in {"en", "es-419"})


# Filters: General
async def test_filter_languages(subs: SubtitleList):
    results = subs.filter(language="es")
    assert all(s.language.startswith("es") for s in results)


async def test_filter_extension(subs: SubtitleList):
    results = subs.filter(extension="vtt")
    assert all(s.extension == "vtt" for s in results)
