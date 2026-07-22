import pytest

from remora._internal.extractor import MediaExtractor
from remora.models.media.item import Media


@pytest.fixture
async def media(mock_extractor) -> Media:
    """Fixture to extract the mock media once for all stream tests."""
    mock_extractor("youtube_video.json")
    data = await MediaExtractor().extract("")
    assert isinstance(data, Media)
    return data


async def test_media(media):
    assert media.id == "HVmeWkqIYqo"
    assert media.title == "¿Por qué no podemos imaginar COLORES nuevos?"
    assert media.duration == 629
    assert len(media.streams) > 0


async def test_uploader(media):
    uploader = media.uploader
    assert uploader is not None
    assert uploader.id == "@curiosamente"
    assert str(uploader.url) == "https://www.youtube.com/@curiosamente"


async def test_channel(media):
    channel = media.channel
    assert channel is not None
    assert channel.id == "UCX16cLWl6dCjlZMgUBxgGkA"
    assert (
        str(channel.url) == "https://www.youtube.com/channel/UCX16cLWl6dCjlZMgUBxgGkA"
    )
    assert channel.is_verified is True
    assert channel.followers == 4620000
