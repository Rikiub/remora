import time
from dataclasses import dataclass

import anyio
from typing_extensions import override

from remora._internal.downloader.event_streamer import AsyncEventStreamer
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.types import StreamContext
from remora.exceptions import DownloaderError
from remora.models.event import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    BatchStreamEvent,
    StreamProgressEvent,
)
from remora.models.stream import AudioStream, VideoStream
from remora.types import DEFAULT_RETRIES


@dataclass(slots=True)
class StreamManager(StreamContext):
    event: StreamProgressEvent | None = None


class MuxedStreamDownloader(AsyncEventStreamer[BatchStreamEvent]):
    SYNC_INTERVAL = 0.5

    def __init__(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(buffer_size=30)

        self.video = StreamManager(stream=video.stream, path=video.path)
        self.audio = StreamManager(stream=audio.stream, path=audio.path)

        self.retries = retries
        self.last_sync_time = 0.0

    @override
    async def _run_pipeline(self) -> None:
        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._download_video)
                tg.start_soon(self._download_audio)
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
        ).start() as progress:
            async for event in progress:
                if event.status == "downloading":
                    self.video.event = event
                    await self._sync_progress()
                elif event.status == "completed":
                    self.video.path = event.file_path
                    await self._sync_progress(True)

    async def _download_audio(self) -> None:
        async with StreamDownloader(
            output_path=self.audio.path,
            stream=self.audio.stream,
            retries=self.retries,
        ).start() as progress:
            async for event in progress:
                if event.status == "downloading":
                    self.audio.event = event
                    await self._sync_progress()
                elif event.status == "completed":
                    self.audio.path = event.file_path
                    await self._sync_progress(True)

    async def _sync_progress(self, force: bool = False) -> None:
        now = time.monotonic()

        # If we aren't forcing an update, and the interval hasn't passed, skip.
        if not force and (now - self.last_sync_time) < self.SYNC_INTERVAL:
            return

        self.last_sync_time = now

        # Collect streams
        streams = [s for s in (self.video.event, self.audio.event) if s]

        # Send event
        await self._emit(BatchStreamDownloading(streams=streams))
