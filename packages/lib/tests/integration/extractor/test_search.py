from remora._internal.extractor import MediaExtractor
from remora.models.media.item import Media
from remora.models.media.list import Playlist

DEFAULT_QUERY = "Sub Urban - Rabbit Hole"


# General
async def test_resolve_medias(extractor: MediaExtractor):
    result = await extractor.extract_search("If Nevermore", service="ytmusic")
    entries = result.entries.medias()
    assert len(entries) >= 1

    for entry in entries:
        entry = await extractor.extract(entry)
        assert isinstance(entry, Media)


async def test_resolve_playlists(extractor: MediaExtractor):
    result = await extractor.extract_search("If Nevermore", service="ytmusic")
    entries = result.entries.playlists()
    assert len(entries) >= 1

    for entry in entries:
        entry = await extractor.extract(entry)
        assert isinstance(entry, Playlist)


# Sites
async def test_youtube(extractor: MediaExtractor):
    await extractor.extract_search(query=DEFAULT_QUERY, service="youtube")


async def test_ytmusic(extractor: MediaExtractor):
    await extractor.extract_search(DEFAULT_QUERY, service="ytmusic")


async def test_soundcloud(extractor: MediaExtractor):
    await extractor.extract_search(DEFAULT_QUERY, service="soundcloud")
