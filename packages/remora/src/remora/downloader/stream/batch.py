import time
from collections.abc import Iterable
from dataclasses import dataclass

import anyio
from typing_extensions import override

from remora._types import _T, StreamContext
from remora.constants import DEFAULT_RETRIES
from remora.downloader._state_streamer import AsyncStateStreamer
from remora.downloader.stream.base import _DEFAULT_BUFFER_SIZE
from remora.downloader.stream.main import StreamDownloader
from remora.exceptions import DownloaderError
from remora.models.options.network import NetworkOptions
from remora.models.progress import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    BatchStreamState,
    StreamProgressState,
)

__all__ = ["BatchStreamDownloader"]


@dataclass(slots=True)
class _StreamManager(StreamContext[_T]):
    state: StreamProgressState | None = None


class BatchStreamDownloader(AsyncStateStreamer[BatchStreamState]):
    SYNC_INTERVAL = 0.5

    def __init__(
        self,
        stream: Iterable[StreamContext],
        retries: int = DEFAULT_RETRIES,
        network_options: NetworkOptions | None = None,
    ):
        super().__init__(buffer_size=_DEFAULT_BUFFER_SIZE)

        self.streams = [_StreamManager(stream=s.stream, path=s.path) for s in stream]
        self.network_options = network_options
        self.retries = retries

        self._last_sync_time = 0.0

    @override
    async def _run_pipeline(self) -> None:
        try:
            async with anyio.create_task_group() as tg:
                for ctx in self.streams:
                    tg.start_soon(self._download, ctx)
        except* DownloaderError as eg:
            raise eg.exceptions[0]
        finally:
            # Safety measure to ensure one last sync happens
            await self._sync_progress(force=True)

        await self._emit(
            BatchStreamCompleted(
                paths=[a.path for a in self.streams],
            )
        )

    async def _download(self, ctx: _StreamManager) -> None:
        async with StreamDownloader(
            output_path=ctx.path,
            stream=ctx.stream,
            retries=self.retries,
            network_options=self.network_options,
        ) as progress:
            async for state in progress:
                if state.status == "downloading":
                    ctx.state = state
                    await self._sync_progress()
                elif state.status == "completed":
                    ctx.path = state.file_path
                    await self._sync_progress(True)

    async def _sync_progress(self, force: bool = False) -> None:
        now = time.monotonic()

        # If we aren't forcing an update, and the interval hasn't passed, skip.
        if not force and (now - self._last_sync_time) < self.SYNC_INTERVAL:
            return

        self._last_sync_time = now

        # Collect streams
        contexts = (a.state for a in self.streams)
        streams = [s for s in contexts if s]

        # Send state
        await self._emit(BatchStreamDownloading(streams=streams))
