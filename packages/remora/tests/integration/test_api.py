from pathlib import Path

import pytest

from remora import DownloadOptions, Remora

# Disabled for now
pytestmark = pytest.mark.skip

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


async def test_single_media(tmp_path: Path):
    remora = Remora(
        download_options=DownloadOptions(
            output_template=tmp_path,
            format_type="audio",
            quality=1,
        ),
    )

    result = await remora.extract(URL)
    assert result.type == "media"

    async with remora.download_media(result) as progress:
        async for state in progress:
            if state.status == "completed":
                assert state.file_path.is_file()
            elif state.status == "failed":
                raise AssertionError(state.message)


async def test_playlist(tmp_path: Path):
    remora = Remora(
        download_options=DownloadOptions(
            output_template=tmp_path,
            format_type="audio",
            quality=1,
        ),
    )

    async with remora.download_batch(PLAYLIST) as progress:
        async for state in progress:
            if state.type == "media" and state.status == "completed":
                assert state.file_path.is_file()
            elif state.status == "failed":
                raise AssertionError(state.message)
