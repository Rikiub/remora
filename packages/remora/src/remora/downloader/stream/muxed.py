import time
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
from remora.models.stream import AudioStream, VideoStream

__all__ = ["MuxedStreamDownloader"]


@dataclass(slots=True)
class StreamManager(StreamContext[_T]):
    state: StreamProgressState | None = None


class MuxedStreamDownloader(AsyncStateStreamer[BatchStreamState]):
    SYNC_INTERVAL = 0.5

    def __init__(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
        retries: int = DEFAULT_RETRIES,
        network_options: NetworkOptions | None = None,
    ):
        super().__init__(buffer_size=_DEFAULT_BUFFER_SIZE)

        self.video = StreamManager[VideoStream](stream=video.stream, path=video.path)
        self.audio = StreamManager[AudioStream](stream=audio.stream, path=audio.path)

        self.network_options = network_options
        self.retries = retries
        self.last_sync_time = 0.0

    @override
    async def _run_pipeline(self) -> None:
        try:
            async with anyio.create_task_group() as tg:
                name = self.__class__.__name__
                tg.start_soon(
                    self._download_video,
                    name=f"{name}.video({self.video.stream.id})",
                )
                tg.start_soon(
                    self._download_audio,
                    name=f"{name}.audio({self.audio.stream.id})",
                )
        except* DownloaderError as eg:
            raise eg.exceptions[0]
        finally:
            # Safety measure to ensure one last sync happens
            await self._sync_progress(force=True)

        await self._emit(
            BatchStreamCompleted(
                video_path=self.video.path,
                audio_path=self.audio.path,
            )
        )

    async def _download_video(self) -> None:
        async with StreamDownloader(
            output_path=self.video.path,
            stream=self.video.stream,
            retries=self.retries,
            network_options=self.network_options,
        ) as progress:
            async for state in progress:
                if state.status == "downloading":
                    self.video.state = state
                    await self._sync_progress()
                elif state.status == "completed":
                    self.video.path = state.file_path
                    await self._sync_progress(True)

    async def _download_audio(self) -> None:
        async with StreamDownloader(
            output_path=self.audio.path,
            stream=self.audio.stream,
            retries=self.retries,
            network_options=self.network_options,
        ) as progress:
            async for state in progress:
                if state.status == "downloading":
                    self.audio.state = state
                    await self._sync_progress()
                elif state.status == "completed":
                    self.audio.path = state.file_path
                    await self._sync_progress(True)

    async def _sync_progress(self, force: bool = False) -> None:
        now = time.monotonic()

        # If we aren't forcing an update, and the interval hasn't passed, skip.
        if not force and (now - self.last_sync_time) < self.SYNC_INTERVAL:
            return

        self.last_sync_time = now

        # Collect streams
        streams = [s for s in (self.video.state, self.audio.state) if s]

        # Send state
        await self._emit(BatchStreamDownloading(streams=streams))
