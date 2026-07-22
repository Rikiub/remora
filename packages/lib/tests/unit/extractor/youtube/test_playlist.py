import pytest

from remora.models.media.list import Playlist


@pytest.fixture
async def playlist(extract_ydl) -> Playlist:
    data = await extract_ydl("youtube/playlist.json")
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

        assert media.title is not None
        assert media.duration is not None

        assert media.uploader is not None
        assert media.channel is not None
        assert media.metrics is not None

        assert len(media.thumbnails) > 0
