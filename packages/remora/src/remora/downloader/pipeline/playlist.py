from collections.abc import Iterable

import anyio
from loguru import logger
from typing_extensions import override

from remora.constants import (
    DEFAULT_MEDIA_CONCURRENCY,
    DEFAULT_POSTPROCESS_CONCURRENCY,
)
from remora.downloader.pipeline._logs import log_event_playlist
from remora.downloader.pipeline.base import BaseDownloader
from remora.downloader.pipeline.media import MediaDownloader
from remora.downloader.session import DownloadSession
from remora.exceptions import ExtractorError
from remora.extractor import MediaExtractor
from remora.models.media import (
    AnyExtractResult,
    Entries,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
)
from remora.models.media.list import _BaseEntries
from remora.models.progress import (
    BatchState,
    MediaEnded,
    MediaExtracting,
    MediaFailed,
    PlaylistCompleted,
    PlaylistEnded,
    PlaylistInProgress,
    PlaylistStarted,
)
from remora.models.types import StrUrl
from remora.template import format_template

__all__ = ["PlaylistDownloader"]


class PlaylistDownloader(BaseDownloader[BatchState]):
    def __init__(
        self,
        item: StrUrl | AnyExtractResult,
        session: DownloadSession,
    ):
        super().__init__(session)

        # Internals
        network_concurrency = (
            self.session.options.download.concurrency or DEFAULT_MEDIA_CONCURRENCY
        )
        self._buffer_size = 100 * network_concurrency

        self._extractor = MediaExtractor(self.session.ydl_context)
        self._unresolved_item = item

        # Limiters
        network_limiter = session.limiters.download or anyio.CapacityLimiter(
            network_concurrency
        )
        self._extract_limiter = network_limiter
        self._download_limiter = network_limiter
        self._postprocess_limiter = (
            session.limiters.postprocess
            or anyio.CapacityLimiter(DEFAULT_POSTPROCESS_CONCURRENCY)
        )

        # Fields
        self.id: str
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None

        self.completed: int
        self.total: int

        self.failed: int

    @override
    async def _emit(self, state) -> None:
        await log_event_playlist(state)
        await super()._emit(state)

    @override
    async def _run_pipeline(self) -> None:
        await self._setup()

        with logger.contextualize(
            list_id=self.id,
            list_title=self.playlist.title if self.playlist else None,
            list_total=len(self.medias),
        ):
            await self._emit(
                PlaylistStarted(
                    id=self.id,
                    completed=self.completed,
                    total=self.total,
                )
            )

            async with anyio.create_task_group() as tg:
                for media in self.medias:
                    tg.start_soon(self._worker, media)

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

    async def _worker(self, media: LazyMedia):
        # Resolve media
        resolved_media = None

        if type(media) is LazyMedia:
            async with self._extract_limiter:
                await self._emit(MediaExtracting(id=media.id, media=media))

                try:
                    resolved_media = await self._extractor.extract(media)
                except ExtractorError as error:
                    self.failed += 1

                    await self._emit(
                        MediaFailed(id=media.id, media=media, message=str(error))
                    )
                    await self._emit(MediaEnded(id=media.id, media=media))
        elif isinstance(media, Media):
            resolved_media = media

        if resolved_media:
            # Start downloader
            async with MediaDownloader(resolved_media, self.session) as progress:
                async for state in progress:
                    if isinstance(state, MediaFailed):
                        self.failed += 1
                    elif isinstance(state, MediaEnded):
                        self.completed += 1
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
            item = await self._extractor.extract(self._unresolved_item)
        else:
            item = self.medias or self._unresolved_item

        # Determine if is a playlist
        playlist = None

        if type(item) is LazyPlaylist:
            playlist = await self._extractor.extract(item)
        elif isinstance(item, Playlist):
            playlist = item

        # Unpack and get the list
        medias: list[LazyMedia]

        match item:
            case LazyMedia():
                medias = [item]
            case _BaseEntries():  # Playlist and SearchList
                medias = list(item.entries.medias())
            case Entries():
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
            self.session.options.download = self.session.options.download.model_copy(
                update={
                    "output_template": format_template(
                        self.session.options.download.output_template,
                        playlist=playlist,
                    )
                }
            )
        else:
            import uuid

            # Generate ID to have unique hash
            id = str(uuid.uuid4())[:8]
            self.id = f"job-{id}"
