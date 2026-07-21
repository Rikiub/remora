from remora._internal.extractor import MediaExtractor
from remora.models.media.item import Media
from remora.models.metadata.social import Channel, Uploader


async def test_extract_youtube(mock_extractor):
    mock_extractor("youtube_video.json")

    extractor = MediaExtractor()
    media = await extractor.extract("")

    assert isinstance(media, Media)
    assert media.id == "HVmeWkqIYqo"
    assert media.title == "¿Por qué no podemos imaginar COLORES nuevos?"
    assert media.duration == 629

    validate_uploader(media.uploader)
    validate_channel(media.channel)

    assert len(media.streams) > 0


def validate_uploader(uploader: Uploader | None):
    assert uploader is not None
    assert uploader.id == "@curiosamente"
    assert str(uploader.url) == "https://www.youtube.com/@curiosamente"


def validate_channel(channel: Channel | None):
    assert channel is not None
    assert channel.id == "UCX16cLWl6dCjlZMgUBxgGkA"
    assert (
        str(channel.url) == "https://www.youtube.com/channel/UCX16cLWl6dCjlZMgUBxgGkA"
    )
    assert channel.is_verified is True
    assert channel.followers == 4620000
