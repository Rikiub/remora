from collections.abc import Iterable

import anyio
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.event_streamer import AsyncEventStreamer
from remora._internal.downloader.logs import log_event_playlist
from remora._internal.downloader.pipeline import DownloadPipeline
from remora._internal.extractor import MediaExtractor
from remora._internal.template.output import format_template
from remora.models.download_options import DownloadOptions
from remora.models.event import (
    BatchEvent,
    MediaCompleted,
    MediaFailed,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
)
from remora.models.media import (
    AnyExtractResult,
    EntriesList,
    LazyMedia,
    LazyPlaylist,
    Playlist,
)
from remora.models.media.list import _BaseList


class DownloadBatch(AsyncEventStreamer[BatchEvent]):
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

        # Setup buffer
        super().__init__(buffer_size=100 * self.config.max_workers)

        # Fields
        self.id: str
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None

        self.completed: int
        self.totat: int

        self.failed: int

    @override
    async def _run_pipeline(self):
        await self._setup()

        await self._emit(
            PlaylistStarted(
                id=self.id,
                completed=self.completed,
                total=self.total,
            )
        )

        with logger.contextualize(
            list_id=self.id,
            list_title=self.playlist.title if self.playlist else None,
            list_total=len(self.medias),
        ):
            async with anyio.create_task_group() as tg:
                for media in self.medias:
                    tg.start_soon(self._pipeline, media)

        await self._emit(
            PlaylistCompleted(
                id=self.id,
                completed=self.completed,
                total=self.total,
                result="partial" if self.failed else "success",
            )
        )

    async def _pipeline(self, media: LazyMedia):
        async with self.limiter:
            async with DownloadPipeline(
                media,
                self.config,
                self.extractor,
            ) as progress:
                async for event in progress:
                    if isinstance(event, MediaCompleted):
                        self.completed += 1
                    elif isinstance(event, MediaFailed):
                        self.failed += 1
                    await self._emit(event)

            await self._emit(
                PlaylistInProgress(
                    id=self.id,
                    completed=self.completed,
                    total=self.total,
                )
            )

    async def _setup(self):
        item = self.medias or self._item

        # Determine if is a playlist
        playlist = None

        if type(item) is LazyPlaylist:
            playlist = await self.extractor.extract(item)
        elif isinstance(item, Playlist):
            playlist = item

        # Unpack and get the list
        medias: list[LazyMedia]

        match item:
            case LazyMedia():
                medias = [item]
            case _BaseList():  # Playlist and SearchList
                medias = list(item.entries.medias())
            case EntriesList():
                medias = list(item.medias())
            case Iterable():
                medias = list(item)
            case _:
                raise TypeError("Unable to unpack media.")

        # Reset
        self.medias = medias
        self.playlist = playlist

        self.completed = 0
        self.total = len(self.medias)

        self.success = 0
        self.failed = 0

        # Set config
        if playlist:
            self.id = playlist.id

            template = format_template(
                self.config.output_template,
                playlist=playlist,
            )
            self.config = self.config.model_copy(
                update={"output_template": template},
            )
        else:
            import secrets

            self.id = secrets.token_urlsafe(6)

    @override
    async def _on_cancelled(self):
        await self._emit(
            PlaylistCancelled(
                id=self.id,
                completed=self.completed,
                total=self.total,
            )
        )

    @override
    async def _emit(self, event):
        await log_event_playlist(event)
        await super()._emit(event)
