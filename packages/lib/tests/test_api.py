from pathlib import Path

import pytest

from remora import DownloadOptions, Remora

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


async def test_single(tmp_path: Path):
    remora = Remora(
        download_options=DownloadOptions(
            output_template=tmp_path,
            format="audio",
            quality=1,
        ),
    )

    async for event in remora.download(URL):
        if event.status == "completed":
            assert event.file_path.is_file()
        elif event.status == "failed":
            raise AssertionError(f"Download failed: {event.message}")


async def test_list(tmp_path: Path):
    remora = Remora(
        download_options=DownloadOptions(
            output_template=tmp_path,
            format="audio",
            quality=1,
        ),
    )

    async for event in remora.download_batch(PLAYLIST):
        if event.type == "media" and event.status == "completed":
            assert event.file_path.is_file()
        elif event.status == "failed":
            raise AssertionError(f"Download failed: {event.message}")


class TestDownloadOptions:
    def test_output_template(self):
        with pytest.raises(ValueError):
            DownloadOptions(output_template="{wrong_key}")

    def test_ffmpeg(self):
        with pytest.raises(ValueError):
            DownloadOptions(ffmpeg_path="{wrong_key}")

    def test_format(self):
        DownloadOptions(format="mp3")
        DownloadOptions(format="mka")
