import pytest

from remora._internal.extractor import MediaExtractor


async def test_youtube(extractor: MediaExtractor):
    await extractor.extract("https://www.youtube.com/watch?v=lBVhLcfoahw")


async def test_ytmusic(extractor: MediaExtractor):
    await extractor.extract("https://music.youtube.com/watch?v=Kx7B-XvmFtE")


async def test_soundcloud(extractor: MediaExtractor):
    await extractor.extract("https://api.soundcloud.com/tracks/1269676381")


@pytest.mark.skip("Sign In required")
async def test_facebook(extractor: MediaExtractor):
    await extractor.extract(
        "https://www.facebook.com/share/v/wfwaBTuUg2eWpd6m/?mibextid=rS40aB7S9Ucbxw6v"
    )


async def test_tiktok(extractor: MediaExtractor):
    await extractor.extract(
        "https://www.tiktok.com/@livewallpaper77/video/7410777368064806149"
    )


async def test_reddit(extractor: MediaExtractor):
    await extractor.extract(
        "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
    )


async def test_pinterest(extractor: MediaExtractor):
    await extractor.extract("https://www.pinterest.com/pin/762304674460692892/")


async def test_netease_music(extractor: MediaExtractor):
    await extractor.extract("http://music.163.com/#/song?id=421563082")
