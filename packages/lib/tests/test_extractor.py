import pytest
from remora.exceptions import ExtractError
from remora.extractor import MediaExtractor
from remora.models.content.list import Playlist
from remora.models.content.media import Media
from remora.ydl.extractor import SEARCH_SERVICE

EXTRACTOR = MediaExtractor(use_cache=False)


def extract_url(url: str) -> Media | Playlist:
    result = EXTRACTOR.extract_url(url)
    return result


def extract_search(
    query: str = "Sub Urban - Rabbit Hole",
    service: SEARCH_SERVICE = "youtube",
):
    search = EXTRACTOR.extract_search(query, service)
    assert len(search.entries) >= 1
    return search


class TestExceptions:
    def test_invalid_url(self):
        with pytest.raises(ExtractError):
            extract_url("https://unkdown.link.com/")

    def test_private_video(self):
        with pytest.raises(ExtractError):
            extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")

    def test_deleted_video(self):
        with pytest.raises(ExtractError):
            extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")


class TestBase:
    def test_media(self):
        result = extract_url("https://youtube.com/watch?v=Kx7B-XvmFtE")
        assert isinstance(result, Media)

    def test_playlist(self):
        result = extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(result, Playlist)


class TestSearch:
    def test_youtube(self):
        extract_search(service="youtube")

    def test_ytmusic(self):
        extract_search(service="ytmusic")

    def test_soundcloud(self):
        extract_search(service="soundcloud")

    def test_resolve_medias(self):
        result = extract_search("If Nevermore", service="ytmusic")

        assert len(result.medias) >= 1

        for entry in result.medias:
            entry = EXTRACTOR.resolve(entry)
            assert isinstance(entry, Media)

    def test_resolve_playlists(self):
        result = extract_search("If Nevermore", service="ytmusic")

        assert len(result.playlists) >= 1

        for entry in result.playlists:
            entry = EXTRACTOR.resolve(entry)
            assert isinstance(entry, Playlist)


class TestSite:
    def test_youtube(self):
        extract_url("https://www.youtube.com/watch?v=lBVhLcfoahw ")

    def test_ytmusic(self):
        extract_url("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    def test_soundcloud(self):
        extract_url("https://api.soundcloud.com/tracks/1269676381")

    """
    [facebook] 2868837949958495: Cannot parse data;
    
    def test_facebook(self):
        extract_url(
            "https://www.facebook.com/share/v/wfwaBTuUg2eWpd6m/?mibextid=rS40aB7S9Ucbxw6v"
        )
    """

    def test_tiktok(self):
        extract_url("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")

    def test_reddit(self):
        extract_url(
            "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
        )

    def test_pinterest(self):
        extract_url("https://www.pinterest.com/pin/762304674460692892/")
