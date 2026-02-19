import pathlib
from collections.abc import AsyncIterable

import anyio
from anyio import Path
from anyio.to_thread import run_sync
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora._internal.ydl.types import PROTOCOLS
from remora.models.event.stream import (
    CompletedStream,
    DownloadingStream,
    StreamEvent,
)
from remora.models.stream.item import Stream
from remora.types import DEFAULT_RETRIES, StrPath


class YDLStreamDownloader(BaseStreamDownloader):
    SUPPORTED_PROTOCOLS = PROTOCOLS

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(output_path, stream, retries=retries)
        self._event = DownloadingStream()

    @override
    async def download(self) -> AsyncIterable[StreamEvent]:  # type: ignore
        self._log_stream()
        self._send_stream, receive_stream = anyio.create_memory_object_stream[
            StreamEvent
        ](30)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._producer)

                async for event in receive_stream:
                    yield event

                yield CompletedStream(file_path=pathlib.Path(self.file_path))

    async def _producer(self):
        from remora._internal.ydl.downloader import download_format

        async with self._send_stream:
            path = await run_sync(
                download_format,
                self.file_path,
                self.stream.to_ydl_dict(),
                self._ydl_progress,
                self.retries,
            )
            self.file_path = Path(path)

    def _ydl_progress(self, data: dict) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        d = data
        event = self._event

        match d["status"]:
            case "downloading":
                downloaded_bytes = d.get("downloaded_bytes") or 0
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

                if downloaded_bytes > event.downloaded:
                    event.downloaded = downloaded_bytes

                if total_bytes > event.total:
                    event.total = total_bytes

                event.speed = d.get("speed") or 0
                event.elapsed = d.get("elapsed") or 0
            case "finished":
                event.downloaded = event.total

        try:
            self._send_stream.send_nowait(event)
        except anyio.WouldBlock:
            pass
