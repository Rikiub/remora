import pytest

from remora.models.media.item import Media


@pytest.fixture
async def media(extract_ydl) -> Media:
    data = await extract_ydl("youtube/video.json")
    assert isinstance(data, Media)
    return data


async def test_media(media: Media):
    assert media.id == "dQw4w9WgXcQ"
    assert (
        media.title
        == "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
    )
    assert media.duration == 213
    assert media.metrics.views == 1795168772
    assert len(media.streams) > 0


async def test_uploader(media: Media):
    uploader = media.uploader
    assert uploader is not None
    assert uploader.name == "Rick Astley"
    assert uploader.id == "@RickAstleyYT"
    assert str(uploader.url) == "https://www.youtube.com/@RickAstleyYT"


async def test_channel(media: Media):
    channel = media.channel
    assert channel is not None
    assert channel.name == "Rick Astley"
    assert channel.id == "UCuAXFkgsw1L7xaCfnd5JJOw"
    assert (
        str(channel.url) == "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw"
    )
    assert channel.is_verified is True
    assert channel.followers
