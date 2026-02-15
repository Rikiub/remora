from pathlib import Path

import pytest
from remora.downloader.main import MediaDownloader
from remora.extractor import MediaExtractor


@pytest.fixture
async def download(tmp_path: Path):
    async def wrap(url: str):
        extractor = MediaExtractor(use_cache=False)
        result = await extractor.extract_url(url)

        async for event in MediaDownloader(
            quality=1,
            output=tmp_path,
            extractor=extractor,
        ).download_batch(result):
            if event.type == "media" and event.status == "finished":
                if not event.filepath.is_file():
                    raise FileNotFoundError(event.filepath)
            else:
                raise AssertionError("Invalid event")

    return wrap


async def test_media(download):
    await download("https://youtube.com/watch?v=Kx7B-XvmFtE")


async def test_playlist(download):
    # Playlist: Album - HIVE (Sub Urban)
    await download(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


class TestSite:
    async def test_youtube(self, download):
        # Include subtitles
        await download("https://youtu.be/HVmeWkqIYqo")

    async def test_ytmusic(self, download):
        await download("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    async def test_tiktok(self, download):
        await download(
            "https://www.tiktok.com/@livewallpaper77/video/7410777368064806149"
        )

    async def test_netease_music(self, download):
        await download("http://music.163.com/#/song?id=421563082")

    async def test_bandcamp(self, download):
        await download("https://gourmetdeluxxx.bandcamp.com/track/nocturnal-hooli")

    async def test_soundcloud_playlist(self, download):
        await download(
            "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"
        )
