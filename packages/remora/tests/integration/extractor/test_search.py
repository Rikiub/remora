from remora import Client
from remora.models.media import Media, Playlist

DEFAULT_QUERY = "Sub Urban - Rabbit Hole"


# General
async def test_resolve_medias(client: Client):
    result = await client.extract_search("If Nevermore", service="ytmusic")
    entries = result.entries.medias()
    assert len(entries) >= 1

    for entry in entries:
        entry = await client.extract(entry)
        assert isinstance(entry, Media)


async def test_resolve_playlists(client: Client):
    result = await client.extract_search("If Nevermore", service="ytmusic")
    entries = result.entries.playlists()
    assert len(entries) >= 1

    for entry in entries:
        entry = await client.extract(entry)
        assert isinstance(entry, Playlist)


# Sites
async def test_youtube(client: Client):
    await client.extract_search(query=DEFAULT_QUERY, service="youtube")


async def test_ytmusic(client: Client):
    await client.extract_search(DEFAULT_QUERY, service="ytmusic")


async def test_soundcloud(client: Client):
    await client.extract_search(DEFAULT_QUERY, service="soundcloud")
