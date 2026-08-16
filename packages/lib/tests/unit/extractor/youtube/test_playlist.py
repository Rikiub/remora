import pytest

from remora.models.media.list import Playlist


@pytest.fixture
async def playlist(extract_ydl) -> Playlist:
    data = await extract_ydl("youtube/playlist.json")
    assert isinstance(data, Playlist)
    return data


async def test_playlist(playlist: Playlist):
    assert playlist.extractor.id == "YoutubeTab"
    assert playlist.id == "OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    assert playlist.title == "Album - HIVE"
    assert (
        str(playlist.url)
        == "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


async def test_medias(playlist: Playlist):
    for media in playlist.entries.medias():
        assert media.extractor.id == "Youtube"

        assert media.title
        assert media.duration

        assert media.uploader
        assert media.channel
        assert media.metrics

        assert len(media.thumbnails) > 0
