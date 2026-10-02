from pathlib import Path

import pytest

from remora import Client, DownloadOptions
from remora.models.progress import MediaCompleted, MediaFailed, MediaState


@pytest.fixture
def download(tmp_path: Path):
    async def wrap(url: str):
        remora = Client(
            download_options=DownloadOptions(
                output_template=tmp_path,
                quality=1,
            ),
        )
        result = await remora.extract(url)

        async with remora.download_playlist(result) as progress:
            async for state in progress:
                if isinstance(state, MediaState):
                    if (
                        isinstance(state, MediaCompleted)
                        and not state.file_path.is_file()
                    ):
                        raise FileNotFoundError(state.file_path)
                    elif isinstance(state, MediaFailed):
                        raise AssertionError(state.message)

    return wrap
