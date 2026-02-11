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
from remora.models.progress.list import PlaylistDownloadState, PlaylistState
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
        self.state = PlaylistState(
            id=self.id,
            stage="started",
            completed=0,
            total=len(self.medias),
        )

    async def run(self) -> AsyncIterable[PlaylistDownloadState]:
        send_stream, receive_stream = anyio.create_memory_object_stream[
            PlaylistDownloadState
        ](self.max_workers)
        self._stream = send_stream

        async with anyio.create_task_group() as tg:
            tg.start_soon(self._execute_download)

            async with receive_stream:
                async for state in receive_stream:
                    yield state

    async def _execute_download(self):
        async with self._stream:
            # Setup
            await self._setup()

            # Tasks
            try:
                async with anyio.create_task_group() as tg:
                    for media in self.medias:
                        tg.start_soon(self._run_pipeline, media)
            finally:
                self.state.stage = "completed"
                self._stream.send_nowait(self.state)

    async def _run_pipeline(self, media: LazyMedia):
        async with self.limiter:
            try:
                async for state in DownloadPipeline(
                    media,
                    self.config,
                    self.extractor,
                ).run():
                    self._stream.send_nowait(state)
            except MediaError:
                pass

            self.state.completed += 1
            self._stream.send_nowait(
                PlaylistState(
                    id=self.id,
                    stage="update",
                    completed=self.state.completed,
                    total=self.state.total,
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

        self.medias = medias
        self.playlist = playlist

        # Set config
        if playlist:
            self.id = playlist.id
            self.config.output = generate_output_template(
                self.config.output,
                playlist=playlist,
            )
        else:
            self.id = secrets.token_urlsafe(6)

        self.state.id = self.id
        self.state.stage = "started"
        self.state.completed = 0
        self.state.total = len(self.medias)
        self._stream.send_nowait(self.state)
