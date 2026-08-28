from typing import Self

import anyio
from loguru import logger

from remora.models.media import LazyMedia
from remora.models.progress import (
    BatchState,
    MediaCompleted,
    MediaDownloading,
    MediaEnded,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaSkipped,
    MediaStarted,
    MediaState,
    MediaWarning,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
    Processing,
)
from remora_cli.ui.download_progress import DownloadProgress


class ProgressCallback:
    def __init__(self, disable: bool = False):
        self.disable = disable
        self.progress = DownloadProgress(disable)

    async def __aenter__(self) -> Self:
        self._tg = anyio.create_task_group()
        await self._tg.__aenter__()
        self.progress.start()
        return self

    async def __aexit__(self, *args):
        await self._tg.__aexit__(*args)
        self.progress.stop()

    async def playlist_callback(self, state: BatchState):
        if self.disable:
            return

        # Determine title
        media_title = ""
        if isinstance(state, MediaState):
            media_title = self._media_display_name(state.media)

        # State Match
        with logger.contextualize(media_title=media_title):
            match state:
                # Playlist
                case PlaylistStarted():
                    self.progress.counter.reset(total=state.total)
                case PlaylistInProgress():
                    self.progress.counter.update(completed=state.completed)
                case PlaylistCompleted(result="success"):
                    logger.success("Download completed")
                case PlaylistCompleted(result="partial"):
                    logger.success("Download completed (Some items failed)")

                # Media
                case MediaStarted():
                    self.progress.update(
                        state.id,
                        description=media_title,
                        status="Starting[blink]...[/]",
                    )
                case MediaExtracting():
                    placeholder = "Extracting[blink]...[/]"
                    self.progress.update(
                        state.id,
                        description=media_title or placeholder,
                        status=placeholder,
                    )
                case MediaDownloading():
                    self.progress.update(
                        state.id,
                        description=media_title,
                        status="Downloading",
                        completed=state.progress.downloaded_bytes,
                        total=state.progress.total_bytes,
                    )
                case MediaProcessing():
                    self._processor_callback(state.id, state.progress)
                case MediaWarning():
                    logger.warning("Warning: {}", state.message)
                case MediaFailed():
                    logger.error("Download failed: {}", state.message)
                    self.progress.update(state.id, status="Error")
                case MediaSkipped():
                    logger.success(
                        'Skipped (Exists as "{file_extension}")',
                        file_extension=state.file_extension,
                        icon="🔄",
                    )
                    self.progress.update(state.id, status="Skipped")
                case MediaCompleted(result="success"):
                    logger.success("Completed")
                    self.progress.update(state.id, status="Completed")
                case MediaCompleted(result="partial"):
                    logger.success("Completed (Some data missed)")
                    self.progress.update(state.id, status="Completed")
                case MediaEnded():

                    async def finish_item(state: BatchState):
                        await anyio.sleep(1.0)
                        self.progress.remove_task(state.id)

                    self._tg.start_soon(finish_item, state)

    def _processor_callback(self, id: str, state: Processing):
        self.progress.update(id, status="Processing[blink]...[/]")

        if state.status == "started":
            match state.task:
                case "convert_audio":
                    self.progress.update(id, status="Converting[blink]...[/]")
                case "merge_streams":
                    self.progress.update(id, status="Merging[blink]...[/]")

    def _media_display_name(self, media: LazyMedia) -> str:
        """Get pretty representation of media name."""

        music = media.music

        if music and (music.track and music.artists):
            return f"{music.track} - {music.artists[0]}"
        elif media.title:
            return media.title
        else:
            return ""
