import pytest

from remora._internal.extractor import MediaExtractor
from remora.models.media.item import Media


@pytest.fixture
async def media(mock_extractor) -> Media:
    mock_extractor("youtube/video.json")
    data = await MediaExtractor().extract("")
    assert isinstance(data, Media)
    return data


async def test_media(media):
    assert media.id == "dQw4w9WgXcQ"
    assert (
        media.title
        == "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
    )
    assert media.duration == 213
    assert len(media.streams) > 0


async def test_uploader(media):
    uploader = media.uploader
    assert uploader is not None
    assert uploader.name == "Rick Astley"
    assert uploader.id == "@RickAstleyYT"
    assert str(uploader.url) == "https://www.youtube.com/@RickAstleyYT"


async def test_channel(media):
    channel = media.channel
    assert channel is not None
    assert channel.name == "Rick Astley"
    assert channel.id == "UCuAXFkgsw1L7xaCfnd5JJOw"
    assert (
        str(channel.url) == "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw"
    )
    assert channel.is_verified is True
    assert channel.followers == 4520000
