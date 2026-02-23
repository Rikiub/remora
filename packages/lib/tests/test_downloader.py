from pathlib import Path

import pytest

from remora import DownloadOptions, Remora


@pytest.fixture
def download(tmp_path: Path):
    async def wrap(url: str):
        remora = Remora(
            download_options=DownloadOptions(
                output_template=tmp_path,
                quality=1,
            ),
        )
        result = await remora.extract(url)

        async for event in remora.download_batch(result):
            if event.type == "media":
                if event.status == "completed" and not event.file_path.is_file():
                    raise FileNotFoundError(event.file_path)
                elif event.status == "failed":
                    raise AssertionError(f"Download failed: {event.message}")

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
