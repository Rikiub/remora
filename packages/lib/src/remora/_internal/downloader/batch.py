from collections.abc import AsyncIterable
from copy import copy

import anyio
from loguru import logger

from remora._internal.downloader.pipeline import DownloadPipeline
from remora._internal.extractor import MediaExtractor
from remora._internal.templates.parser import generate_output_template
from remora.exceptions import MediaError
from remora.models.content.list import LazyPlaylist, MediaList, Playlist
from remora.models.content.media import LazyMedia
from remora.models.content.types import AnyExtractResult
from remora.models.download_options import DownloadOptions
from remora.models.event.list import FinishedPlaylist, PlaylistUpdate
from remora.models.event.main import DownloadEvent


class DownloadBatch:
    def __init__(
        self,
        data: AnyExtractResult,
        format_config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        # Internals
        self.config = copy(format_config) or DownloadOptions()
        self.extractor = extractor or MediaExtractor()

        # Parallel
        self.limiter = anyio.CapacityLimiter(self.config.max_workers)

        # Data
        self.id = ""
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None = None
        self._data = data

        # State
        self.completed = 0
        self.total = 0

        self.success = 0
        self.failed = 0

        self.result = "success"

        # Log
        logger.debug(self.config)

    async def download(self) -> AsyncIterable[DownloadEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[DownloadEvent](
            30
        )

        async with receive_stream:
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._producer)

                    async for event in receive_stream:
                        yield event
            except anyio.get_cancelled_exc_class():
                yield await receive_stream.receive()

    async def _producer(self):
        async with self._stream:
            # Setup
            await self._setup()

            await self._stream.send(
                PlaylistUpdate(
                    id=self.id,
                    status="started",
                    completed=self.completed,
                    total=self.total,
                )
            )

            # Tasks
            try:
                async with anyio.create_task_group() as tg:
                    for media in self.medias:
                        tg.start_soon(self._pipeline, media)
            except anyio.get_cancelled_exc_class():
                self.result = "cancelled"
                raise
            finally:
                self._stream.send_nowait(
                    FinishedPlaylist(
                        id=self.id,
                        completed=self.completed,
                        total=self.total,
                        result=self.result,  # type: ignore
                    )
                )

    async def _pipeline(self, media: LazyMedia):
        async with self.limiter:
            try:
                async for event in DownloadPipeline(
                    media,
                    self.config,
                    self.extractor,
                ).download():
                    await self._stream.send(event)

                self.success += 1
            except* MediaError:
                self.result = "incomplete"
                self.failed += 1

            self.completed += 1
            await self._stream.send(
                PlaylistUpdate(
                    id=self.id,
                    status="update",
                    completed=self.completed,
                    total=self.total,
                )
            )

    async def _setup(self):
        data = self._data
        medias = []
        playlist = None

        # Get real data
        if type(data) is LazyPlaylist:
            playlist = await self.extractor.extract(data)
        elif isinstance(data, Playlist):
            playlist = data

        match data:
            case LazyMedia():
                medias: list[LazyMedia] = [data]
            case MediaList():
                medias = data.medias
            case list():
                medias = data
            case _:
                raise TypeError("Unable to unpack media.")

        # Reset
        self.medias = medias
        self.playlist = playlist

        self.completed = 0
        self.total = len(self.medias)

        self.success = 0
        self.failed = 0

        self.result = "success"

        # Set config
        if playlist:
            self.id = playlist.id
            self.config.template = generate_output_template(
                self.config.template,
                playlist=playlist,
            )
        else:
            import secrets

            self.id = secrets.token_urlsafe(6)
