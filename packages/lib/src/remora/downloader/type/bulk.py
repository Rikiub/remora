import concurrent.futures as cf
from copy import copy
import secrets
from pathlib import Path

from loguru import logger

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

        # State
        self.medias, self.playlist = self._resolve_data(data)

        if self.playlist:
            self.id = self.playlist.id
            self.config.output = generate_output_template(
                self.config.output,
                playlist=self.playlist,
            )
        else:
            self.id = secrets.token_urlsafe(6)

    def run(self) -> list[Path]:
        paths: list[Path] = []
        success = 0
        errors = 0

        state = PlaylistState(
            id=self.id,
            stage="started",
            completed=0,
            total=len(self.medias),
        )
        self.on_playlist(state)

        with cf.ThreadPoolExecutor(max_workers=self.threads) as executor:
            state.stage = "update"

            futures = {
                executor.submit(self._run_pipeline, media): media
                for media in self.medias
            }

            try:
                for future in cf.as_completed(futures):
                    try:
                        paths.append(future.result())
                        success += 1
                    except MediaError:
                        errors += 1
                    finally:
                        state.completed += 1
                        self.on_playlist(state)
            except KeyboardInterrupt:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        state.stage = "completed"
        self.on_playlist(state)

        logger.debug(
            "{current} of {total} medias completed. {errors} errors.",
            current=success,
            total=len(self.medias),
            errors=errors,
        )

        return paths

    def _run_pipeline(
        self,
        media: LazyMedia,
    ) -> Path:
        return DownloadPipeline(
            media,
            self.config,
            self.extractor,
            self.on_progress,
        ).run()

    def _resolve_data(
        self, data: MediaResult
    ) -> tuple[list[LazyMedia], Playlist | None]:
        medias = []
        playlist = None

        match data:
            case LazyPlaylist():
                playlist = self.extractor.resolve(data)
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

        return medias, playlist
