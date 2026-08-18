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

        async with remora.download_batch(result) as progress:
            async for event in progress:
                if event.type == "media":
                    if event.status == "completed" and not event.file_path.is_file():
                        raise FileNotFoundError(event.file_path)
                    elif event.status == "failed":
                        raise AssertionError(event.message)

    return wrap
