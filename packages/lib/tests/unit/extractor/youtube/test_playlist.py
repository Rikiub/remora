import pytest

from remora._internal.extractor import MediaExtractor
from remora.models.media.list import Playlist


@pytest.fixture
async def playlist(mock_extractor) -> Playlist:
    mock_extractor("youtube/playlist.json")
    data = await MediaExtractor().extract("")
    assert isinstance(data, Playlist)
    return data


async def test_playlist(playlist: Playlist):
    assert playlist.extractor == "YoutubeTab"
    assert playlist.id == "OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    assert playlist.title == "Album - HIVE"
    assert (
        str(playlist.url)
        == "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


async def test_medias(playlist: Playlist):
    for media in playlist.medias:
        assert media.extractor == "Youtube"

        assert media.title
        assert media.duration

        assert media.uploader
        assert media.channel
        assert media.metrics

        assert len(media.thumbnails) > 0
