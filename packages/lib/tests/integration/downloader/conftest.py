from pathlib import Path

import pytest

from remora._internal.api import Remora
from remora.models.download_options import DownloadOptions


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
