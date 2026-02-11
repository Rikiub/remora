import anyio
from anyio.to_thread import run_sync
from anyio import Path

from remora.exceptions import DownloadError
from remora.ydl.types import SupportedProtocols
from typing_extensions import override

from remora.downloader.format.base import DEFAULT_RETRIES, BaseFormatDownloader
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback, FormatState
from remora.types import StrPath


class YDLFormatDownloader(BaseFormatDownloader):
    SUPPORTED_PROTOCOLS = SupportedProtocols

    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        on_progress: FormatDownloadCallback | None = None,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(filepath, format, on_progress, retries)

        self.send_stream, self.receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=100
        )

    @override
    async def download(self) -> Path:
        from remora.ydl.downloader import download_format

        async with anyio.create_task_group() as tg:
            tg.start_soon(self._progress_consumer)

            try:
                path = await run_sync(
                    download_format,
                    self.filepath,
                    self.format.to_ydl_dict(),
                    lambda data: self.format_state._ydl_progress(
                        data,
                        self._sync_progress,
                    )
                    if self.progress
                    else None,
                )
                path = Path(path)
            except DownloadError:
                raise
            finally:
                await self.send_stream.aclose()

        return path

    def _sync_progress(self, state: FormatState):
        self.format_state = state
        self.send_stream.send_nowait(True)

    async def _progress_consumer(self):
        async with self.receive_stream:
            async for _ in self.receive_stream:
                if self.progress:
                    await self.progress(self.format_state)
