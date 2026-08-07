import time
from collections.abc import AsyncIterable
from dataclasses import dataclass

import anyio

from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.types import StreamContext
from remora.exceptions import DownloaderError
from remora.models.event.stream import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    BatchStreamEvent,
    StreamProgressEvent,
)
from remora.models.stream.item import AudioStream, VideoStream
from remora.types import DEFAULT_RETRIES


@dataclass(slots=True)
class StreamManager(StreamContext):
    event: StreamProgressEvent | None = None


class MuxedStreamDownloader:
    SYNC_INTERVAL = 0.5

    def __init__(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
        retries: int = DEFAULT_RETRIES,
    ):
        self.video = StreamManager(stream=video.stream, path=video.path)
        self.audio = StreamManager(stream=audio.stream, path=audio.path)

        self.retries = retries
        self.last_sync_time = 0.0

    async def download(self) -> AsyncIterable[BatchStreamEvent]:
        self._send_stream, receive_stream = anyio.create_memory_object_stream[
            BatchStreamEvent
        ](30)

        async with receive_stream, anyio.create_task_group() as tg:
            tg.start_soon(self._producer)

            async for event in receive_stream:
                yield event

    async def _producer(self):
        async with self._send_stream:
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._download_video)
                    tg.start_soon(self._download_audio)
            except* DownloaderError as eg:
                raise eg.exceptions[0]
            finally:
                # Safety measure to ensure one last sync happens
                await self._sync_progress(force=True)

            await self._send_stream.send(
                BatchStreamCompleted(
                    video_path=self.video.path,
                    audio_path=self.audio.path,
                )
            )

    async def _download_video(self):
        async for event in StreamDownloader(
            output_path=self.video.path,
            stream=self.video.stream,
            retries=self.retries,
        ).download():
            if event.status == "downloading":
                self.video.event = event
                await self._sync_progress()
            elif event.status == "completed":
                self.video.path = event.file_path
                await self._sync_progress(True)

    async def _download_audio(self):
        async for event in StreamDownloader(
            output_path=self.audio.path,
            stream=self.audio.stream,
            retries=self.retries,
        ).download():
            if event.status == "downloading":
                self.audio.event = event
                await self._sync_progress()
            elif event.status == "completed":
                self.audio.path = event.file_path
                await self._sync_progress(True)

    async def _sync_progress(self, force: bool = False):
        now = time.monotonic()

        # If we aren't forcing an update, and the interval hasn't passed, skip.
        if not force and (now - self.last_sync_time) < self.SYNC_INTERVAL:
            return

        self.last_sync_time = now

        # Collect streams
        streams = [s for s in (self.video.event, self.audio.event) if s]

        # Send event
        if self._send_stream:
            await self._send_stream.send(BatchStreamDownloading(streams=streams))
