import pathlib
from collections.abc import AsyncIterable

import anyio
from anyio import Path
from anyio.to_thread import run_sync
from typing_extensions import override

from remora.downloader.stream.base import DEFAULT_RETRIES, BaseStreamDownloader
from remora.models.event.stream import (
    DownloadingStream,
    FinishedStream,
    StreamEvent,
)
from remora.models.stream.types import Stream
from remora.types import StrPath
from remora.ydl.types import YDL_PROTOCOLS


class YDLStreamDownloader(BaseStreamDownloader):
    SUPPORTED_PROTOCOLS = YDL_PROTOCOLS

    def __init__(
        self,
        filepath: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(filepath, stream, retries=retries)

    @override
    async def download(self) -> AsyncIterable[StreamEvent]:  # type: ignore
        self._log_stream()
        self._send_stream, receive_stream = anyio.create_memory_object_stream[
            StreamEvent
        ](30)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._execute_download)

                async for event in receive_stream:
                    yield event

                yield FinishedStream(filepath=pathlib.Path(self.filepath))

    async def _execute_download(self):
        from remora.ydl.downloader import download_format

        def callback(event):
            try:
                self._send_stream.send_nowait(event)
            except anyio.WouldBlock:
                pass

        async with self._send_stream:
            event = DownloadingStream()

            path = await run_sync(
                download_format,
                self.filepath,
                self.stream.to_ydl_dict(),
                lambda data: event._ydl_progress(data, callback),
            )
            self.filepath = Path(path)
