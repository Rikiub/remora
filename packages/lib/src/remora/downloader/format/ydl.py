import asyncio
from pathlib import Path
import time

from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback, FormatState
from remora.types import StrPath


class YDLFormatDownloader:
    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        on_progress: FormatDownloadCallback | None = None,
    ):
        self.filepath = Path(filepath)
        self.format = format
        self.progress = on_progress

        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        self.state = FormatState()

    async def download(self) -> Path:
        from remora.ydl.downloader import download_format

        consumer_task = asyncio.create_task(self._progress_consumer())

        try:
            path = await download_format(
                self.filepath,
                format_info=self.format.to_ydl_dict(),
                callback=lambda data: self.state._ydl_progress(
                    data,
                    self._sync_progress,
                )
                if self.progress
                else None,
            )
        finally:
            self.queue.put_nowait(None)
            await consumer_task

        return path

    def _sync_progress(self, state: FormatState):
        self.state = state
        self.loop.call_soon_threadsafe(self.queue.put_nowait, True)

    async def _progress_consumer(self):
        last_update = 0
        # Target: 30 FPS = ~0.033s | 60 FPS = ~0.016s
        MIN_INTERVAL = 0.1

        while True:
            # Check queue
            if not await self.queue.get():
                break

            while not self.queue.empty():
                if not self.queue.get_nowait():
                    return

            # Delay for fluid progress
            current_time = time.time()

            if current_time - last_update < MIN_INTERVAL:
                self.queue.task_done()
                continue

            last_update = current_time

            # Send progress to callback
            if self.progress:
                await self.progress(self.state)

            self.queue.task_done()
