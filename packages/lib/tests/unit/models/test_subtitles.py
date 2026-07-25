import pytest

from remora.models.metadata.subtitle import (
    EmbeddedSubtitle,
    ExternalSubtitle,
    SubtitleList,
)


@pytest.fixture
def subs() -> SubtitleList:
    URL = "http://example.com/subtitle"

    return SubtitleList(
        [
            ExternalSubtitle(
                name="English",
                language="en",
                extension="vtt",
                url=URL,
            ),
            ExternalSubtitle(
                name="Spanish",
                language="es",
                extension="vtt",
                url=URL,
            ),
            ExternalSubtitle(
                name="Spanish",
                language="es-419",
                extension="srt",
                url=URL,
            ),
            EmbeddedSubtitle(
                name="Lyrics",
                language="lyrics",
                extension="lrc",
                content="...",
            ),
        ]
    )


# Filters: Type
async def test_externals(subs: SubtitleList):
    assert len(subs.externals()) > 0


async def test_embedded(subs: SubtitleList):
    assert len(subs.embedded()) > 0


async def test_languages(subs: SubtitleList):
    assert all(key in subs.languages() for key in ("en", "es-419"))


# Filters: General
async def test_filter_languages(subs: SubtitleList):
    results = subs.filter(language="es")
    assert all(s.language.startswith("es") for s in results)


async def test_filter_extension(subs: SubtitleList):
    results = subs.filter(extension="vtt")
    assert all(s.extension == "vtt" for s in results)
