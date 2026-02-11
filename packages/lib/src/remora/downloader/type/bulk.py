import secrets
from copy import copy

import anyio
from anyio import Path
from remora.downloader.config import FormatConfig
from remora.downloader.type.pipeline import DownloadPipeline
from remora.exceptions import MediaError
from remora.extractor import MediaExtractor
from remora.models.content.list import LazyPlaylist, MediaList, Playlist
from remora.models.content.media import LazyMedia
from remora.models.content.types import ExtractResult, MediaListEntries
from remora.models.progress.list import PlaylistDownloadCallback, PlaylistState
from remora.models.progress.media import MediaDownloadCallback
from remora.template.parser import generate_output_template

MediaResult = ExtractResult | MediaListEntries | MediaList | list[LazyMedia]


class DownloadBulk:
    def __init__(
        self,
        data: MediaResult,
        format_config: FormatConfig | None = None,
        extractor: MediaExtractor | None = None,
        max_workers: int = 5,
        on_progress: MediaDownloadCallback | None = None,
        on_playlist: PlaylistDownloadCallback | None = None,
    ):
        # Internals
        self.config = copy(format_config) or FormatConfig()
        self.extractor = extractor or MediaExtractor()
        self.semaphore = anyio.Semaphore(max_workers)

        self.on_progress = on_progress
        self._on_playlist = on_playlist

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

    async def run(self) -> list[Path]:
        # Setup
        await self._setup()
        await self.on_playlist(self.state)

        # Tasks
        paths: list[Path] = []
        async with anyio.create_task_group() as tg:
            for media in self.medias:
                tg.start_soon(self._run_pipeline, media, paths)

        # Completed
        self.state.stage = "completed"
        await self.on_playlist(self.state)

        return paths

    async def _run_pipeline(self, media: LazyMedia, results: list[Path]):
        async with self.semaphore:
            try:
                path = await DownloadPipeline(
                    media,
                    self.config,
                    self.extractor,
                    self.on_progress,
                ).run()

                results.append(path)
            except MediaError:
                pass

            self.state.completed += 1
            await self.on_playlist(
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

    async def on_playlist(self, state: PlaylistState):
        if self._on_playlist:
            await self._on_playlist(state)
