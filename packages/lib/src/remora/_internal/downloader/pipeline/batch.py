from collections.abc import Iterable

import anyio
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.logs import log_event_playlist
from remora._internal.downloader.pipeline.base import Downloader
from remora._internal.downloader.pipeline.media import MediaDownloader
from remora._internal.extractor import MediaExtractor
from remora._internal.template.output import format_template
from remora.models.download_options import DownloadOptions
from remora.models.media import (
    AnyExtractResult,
    EntriesList,
    LazyMedia,
    LazyPlaylist,
    Playlist,
)
from remora.models.media.list import _BaseList
from remora.models.progress import (
    BatchState,
    MediaCompleted,
    MediaFailed,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistEnded,
    PlaylistInProgress,
    PlaylistStarted,
)
from remora.types import StrUrl


class BatchDownloader(Downloader[BatchState]):
    def __init__(
        self,
        item: StrUrl | AnyExtractResult,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        # Internals
        super().__init__(
            config=config,
            extractor=extractor,
        )
        self._buffer_size = 100 * self.config.max_workers

        self.limiter = anyio.CapacityLimiter(self.config.max_workers)
        self._unresolved_item = item

        # Fields
        self.id: str
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None

        self.completed: int
        self.totat: int

        self.failed: int

    @override
    async def _emit(self, state) -> None:
        await log_event_playlist(state)
        await super()._emit(state)

    @override
    async def _on_cancelled(self) -> None:
        await self._emit(
            PlaylistCancelled(
                id=self.id,
                completed=self.completed,
                total=self.total,
            )
        )

    @override
    async def _run_pipeline(self) -> None:
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
                    worker = MediaDownloader(
                        media,
                        self.config,
                        self.extractor,
                    )
                    tg.start_soon(self._worker, worker)

        await self._emit(
            PlaylistCompleted(
                id=self.id,
                completed=self.completed,
                total=self.total,
                result="partial" if self.failed else "success",
            )
        )
        await self._emit(
            PlaylistEnded(
                id=self.id,
                completed=self.completed,
                total=self.total,
            )
        )

    async def _worker(self, downloader: MediaDownloader):
        async with self.limiter:
            async with downloader as progress:
                async for state in progress:
                    if isinstance(state, MediaCompleted):
                        self.completed += 1
                    elif isinstance(state, MediaFailed):
                        self.failed += 1
                    await self._emit(state)

            await self._emit(
                PlaylistInProgress(
                    id=self.id,
                    completed=self.completed,
                    total=self.total,
                )
            )

    async def _setup(self):
        if isinstance(self._unresolved_item, StrUrl):
            item = await self.extractor.extract(self._unresolved_item)
        else:
            item = self.medias or self._unresolved_item

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
            import uuid

            # Generate ID to have unique hash
            id = str(uuid.uuid4)[:8]
            self.id = f"job-{id}"
