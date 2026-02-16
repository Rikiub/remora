import pytest

from remora.exceptions import ExtractError
from remora.extractor import MediaExtractor
from remora.models.content.list import Playlist
from remora.models.content.media import Media
from remora.ydl.extractor import SearchService

EXTRACTOR = MediaExtractor(use_cache=False)


async def extract(url: str) -> Media | Playlist:
    result = await EXTRACTOR.extract(url)
    return result


async def extract_search(
    query: str = "Sub Urban - Rabbit Hole",
    service: SearchService = "youtube",
):
    search = await EXTRACTOR.extract_search(query, service)
    assert len(search.entries) >= 1
    return search


class TestExceptions:
    async def test_invalid_url(self):
        with pytest.raises(ExtractError):
            await extract("https://unkdown.link.com/")

    async def test_private_video(self):
        with pytest.raises(ExtractError):
            await extract("https://www.youtube.com/watch?v=yi50KlsCBio")

    async def test_deleted_video(self):
        with pytest.raises(ExtractError):
            await extract("https://www.youtube.com/watch?v=JUf1zxjR_Qw")


class TestBase:
    async def test_media(self):
        result = await extract("https://youtube.com/watch?v=Kx7B-XvmFtE")
        assert isinstance(result, Media)

    async def test_playlist(self):
        result = await extract(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(result, Playlist)


class TestSearch:
    async def test_youtube(self):
        await extract_search(service="youtube")

    async def test_ytmusic(self):
        await extract_search(service="ytmusic")

    async def test_soundcloud(self):
        await extract_search(service="soundcloud")

    async def test_resolve_medias(self):
        result = await extract_search("If Nevermore", service="ytmusic")

        assert len(result.medias) >= 1

        for entry in result.medias:
            entry = await EXTRACTOR.extract(entry)
            assert isinstance(entry, Media)

    async def test_resolve_playlists(self):
        result = await extract_search("If Nevermore", service="ytmusic")

        assert len(result.playlists) >= 1

        for entry in result.playlists:
            entry = await EXTRACTOR.extract(entry)
            assert isinstance(entry, Playlist)


class TestSite:
    async def test_youtube(self):
        await extract("https://www.youtube.com/watch?v=lBVhLcfoahw")

    async def test_ytmusic(self):
        await extract("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    async def test_soundcloud(self):
        await extract("https://api.soundcloud.com/tracks/1269676381")

    """
    [facebook] 2868837949958495: Cannot parse data;
    
    def test_facebook(self):
        extract_url(
            "https://www.facebook.com/share/v/wfwaBTuUg2eWpd6m/?mibextid=rS40aB7S9Ucbxw6v"
        )
    """

    async def test_tiktok(self):
        await extract(
            "https://www.tiktok.com/@livewallpaper77/video/7410777368064806149"
        )

    async def test_reddit(self):
        await extract(
            "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
        )

    async def test_pinterest(self):
        await extract("https://www.pinterest.com/pin/762304674460692892/")

    async def test_netease_music(self):
        await extract("http://music.163.com/#/song?id=421563082")
