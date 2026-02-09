import asyncio
from copy import copy
import secrets
from pathlib import Path

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
        threads: int = 5,
        on_progress: MediaDownloadCallback | None = None,
        on_playlist: PlaylistDownloadCallback | None = None,
    ):
        # Internals
        self.config = copy(format_config) or FormatConfig()
        self.extractor = extractor or MediaExtractor()
        self.threads = threads

        self.on_progress = on_progress
        self.on_playlist = lambda a: None

        # Callbacks
        if on_playlist:
            self.on_playlist = on_playlist

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
        self.on_playlist(self.state)

        # Tasks
        semaphore = asyncio.Semaphore(self.threads)

        tasks = [self._run_pipeline(media, semaphore) for media in self.medias]
        results = await asyncio.gather(*tasks)

        # Completed
        self.state.stage = "completed"
        self.on_playlist(self.state)

        paths = [p for p in results if p]
        return paths

    async def _run_pipeline(
        self, media: LazyMedia, semaphore: asyncio.Semaphore
    ) -> Path | None:
        async with semaphore:
            try:
                path = await DownloadPipeline(
                    media,
                    self.config,
                    self.extractor,
                    self.on_progress,
                ).run()
            except MediaError:
                path = None

            self.state.completed += 1
            self.on_playlist(
                PlaylistState(
                    id=self.id,
                    stage="update",
                    completed=self.state.completed,
                    total=self.state.total,
                )
            )

            return path

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
