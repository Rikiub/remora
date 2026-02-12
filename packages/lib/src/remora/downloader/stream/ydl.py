import pathlib
from typing import AsyncIterable
import anyio
from anyio import Path
from anyio.to_thread import run_sync
from remora.downloader.stream.base import DEFAULT_RETRIES, BaseStreamDownloader
from remora.models.stream.types import Stream
from remora.models.progress.stream import (
    CompletedStreamState,
    DownloadingStreamState,
    StreamState,
)
from remora.types import StrPath
from remora.ydl.types import SupportedProtocols
from typing_extensions import override


class YDLFormatDownloader(BaseStreamDownloader):
    SUPPORTED_PROTOCOLS = list(SupportedProtocols)

    def __init__(
        self,
        filepath: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(filepath, stream, retries=retries)

    @override
    async def download(self) -> AsyncIterable[StreamState]:  # type: ignore
        self._log_stream()
        self._send_stream, receive_stream = anyio.create_memory_object_stream[
            StreamState
        ](10)

        async with anyio.create_task_group() as tg:
            tg.start_soon(self._execute_download)

            async with receive_stream:
                async for state in receive_stream:
                    yield state

                yield CompletedStreamState(filepath=pathlib.Path(self.filepath))

    async def _execute_download(self):
        from remora.ydl.downloader import download_format

        async with self._send_stream:
            state = DownloadingStreamState()

            path = await run_sync(
                download_format,
                self.filepath,
                self.stream.to_ydl_dict(),
                lambda data: state._ydl_progress(
                    data,
                    lambda state: self._send_stream.send_nowait(state),
                ),
            )
            self.filepath = Path(path)
