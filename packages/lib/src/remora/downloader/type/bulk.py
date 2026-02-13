import secrets
from copy import copy
from typing import AsyncIterable

import anyio
from remora.downloader.config import FormatConfig
from remora.downloader.type.pipeline import DownloadPipeline
from remora.exceptions import MediaError
from remora.extractor import MediaExtractor
from remora.models.content.list import LazyPlaylist, MediaList, Playlist
from remora.models.content.media import LazyMedia
from remora.models.content.types import ExtractResult, MediaListEntries
from remora.models.event.list import FinishedPlaylist, PlaylistUpdate
from remora.models.event.main import DownloadEvent
from remora.template.parser import generate_output_template

MediaResult = ExtractResult | MediaListEntries | MediaList | list[LazyMedia]


class DownloadBulk:
    def __init__(
        self,
        data: MediaResult,
        format_config: FormatConfig | None = None,
        extractor: MediaExtractor | None = None,
        max_workers: int = 5,
    ):
        # Internals
        self.config = copy(format_config) or FormatConfig()
        self.extractor = extractor or MediaExtractor()

        # Parallel
        self.max_workers = max_workers
        self.limiter = anyio.CapacityLimiter(max_workers)

        # Data
        self.id = ""
        self._data = data
        self.medias: list[LazyMedia] = []
        self.playlist: Playlist | None = None

        if self.playlist:
            self.id = self.playlist.id
            self.config.output = generate_output_template(
                self.config.output,
                playlist=self.playlist,
            )
        else:
            self.id = secrets.token_urlsafe(6)

        # State
        self.completed = 0
        self.total = 0

        self.success = 0
        self.failed = 0

        self.result = "success"

    async def run(self) -> AsyncIterable[DownloadEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[DownloadEvent](
            100
        )

        async with receive_stream:
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._execute_download)

                    async for event in receive_stream:
                        yield event
            except anyio.get_cancelled_exc_class():
                yield receive_stream.receive_nowait()

    async def _execute_download(self):
        async with self._stream:
            # Setup
            await self._setup()

            self._stream.send_nowait(
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
                        tg.start_soon(self._run_pipeline, media)
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

    async def _run_pipeline(self, media: LazyMedia):
        async with self.limiter:
            try:
                async for event in DownloadPipeline(
                    media,
                    self.config,
                    self.extractor,
                ).run():
                    self._stream.send_nowait(event)

                self.success += 1
            except* MediaError:
                self.result = "incomplete"
                self.failed += 1

            self.completed += 1
            self._stream.send_nowait(
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
        match data:
            case LazyPlaylist():
                playlist = await self.extractor.resolve(data)
            case Playlist():
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
            self.config.output = generate_output_template(
                self.config.output,
                playlist=playlist,
            )
        else:
            self.id = secrets.token_urlsafe(6)
