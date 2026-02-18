from collections.abc import AsyncIterable

import anyio
from loguru import logger

from remora._internal.downloader.pipeline import DownloadPipeline
from remora._internal.extractor import MediaExtractor
from remora._internal.template.output import format_template
from remora.exceptions import RemoraError
from remora.models.download_options import DownloadOptions
from remora.models.event.playlist import (
    BatchEvent,
    FinishedPlaylist,
    FinishedPlaylistResult,
    PlaylistUpdate,
)
from remora.models.media.item import LazyMedia
from remora.models.media.list import LazyPlaylist, MediaList, Playlist
from remora.models.media.types import AnyExtractResult


class DownloadBatch:
    def __init__(
        self,
        item: AnyExtractResult,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        # Internals
        self.config = config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()
        self.limiter = anyio.CapacityLimiter(self.config.max_workers)
        self._item = item

        # Fields
        self.id: str
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None

        self.completed: int
        self.totat: int

        self.success: int
        self.failed: int

        self.result: FinishedPlaylistResult

        # Log
        logger.debug(self.config)

    async def download(self) -> AsyncIterable[BatchEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[BatchEvent](30)

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
            await self._setup()

            await self._stream.send(
                PlaylistUpdate(
                    id=self.id,
                    status="started",
                    completed=self.completed,
                    total=self.total,
                )
            )

            with logger.contextualize(
                playlist_id=self.id,
                playlist_title=self.playlist.title if self.playlist else None,
                playlist_total=len(self.medias),
            ):
                try:
                    # Tasks
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
                            result=self.result,
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
            except* RemoraError:
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
        item = self.medias or self._item

        # Get real data
        playlist = None

        if type(item) is LazyPlaylist:
            playlist = await self.extractor.extract(item)
        elif isinstance(item, Playlist):
            playlist = item

        match item:
            case LazyMedia():
                medias: list[LazyMedia] = [item]
            case MediaList():
                medias = item.medias
            case list():
                medias = item
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

            template = format_template(
                self.config.output_template,
                playlist=playlist,
            )
            self.config = self.config.model_copy(update={"template": template})
        else:
            import secrets

            self.id = secrets.token_urlsafe(6)
