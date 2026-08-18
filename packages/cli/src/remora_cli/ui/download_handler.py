from typing import Self

import anyio
from loguru import logger

from remora.models.event import (
    BatchEvent,
    MediaCancelled,
    MediaCompleted,
    MediaDownloading,
    MediaEnded,
    MediaEvent,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaSkipped,
    MediaStarted,
    MediaWarning,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
    Processing,
)
from remora.models.media import LazyMedia
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

    async def playlist_callback(self, event: BatchEvent):
        if self.disable:
            return

        # Determine title
        media_title = ""
        if isinstance(event, MediaEvent):
            media_title = self._media_display_name(event.media)

        # Event Match
        with logger.contextualize(media_title=media_title):
            match event:
                # Playlist
                case PlaylistStarted():
                    self.progress.counter.reset(total=event.total)
                case PlaylistInProgress():
                    self.progress.counter.update(completed=event.completed)
                case PlaylistCompleted(result="success"):
                    logger.success("Download completed")
                case PlaylistCompleted(result="partial"):
                    logger.success("Download completed (Some items failed)")
                case PlaylistCancelled():
                    logger.warning("Download cancelled")

                # Media
                case MediaStarted():
                    self.progress.add_task(
                        event.id,
                        description=media_title,
                        status="Starting[blink]...[/]",
                    )
                case MediaExtracting():
                    self.progress.update(
                        event.id,
                        description=media_title or "Extracting[blink]...[/]",
                        status="Extracting[blink]...[/]",
                    )
                case MediaDownloading():
                    self.progress.update(
                        event.id,
                        description=media_title,
                        status="Downloading",
                        completed=event.progress.downloaded_bytes,
                        total=event.progress.total_bytes,
                    )
                case MediaProcessing():
                    self._processor_callback(event.id, event.progress)
                case MediaWarning():
                    logger.warning("Warning: {}", event.message)
                case MediaCancelled():
                    logger.error("Download cancelled")
                    self.progress.update(event.id, status="Cancelled")
                case MediaFailed():
                    logger.error("Download failed: {}", event.message)
                    self.progress.update(event.id, status="Error")
                case MediaSkipped():
                    logger.success(
                        'Skipped (Exists as "{file_extension}")',
                        file_extension=event.file_extension,
                        icon="🔄",
                    )
                    self.progress.update(event.id, status="Skipped")
                case MediaCompleted(result="success"):
                    logger.success("Completed")
                    self.progress.update(event.id, status="Completed")
                case MediaCompleted(result="partial"):
                    logger.success("Completed (Some data missed)")
                    self.progress.update(event.id, status="Completed")
                case MediaEnded():

                    async def finish_item(event: BatchEvent):
                        await anyio.sleep(1.0)
                        self.progress.remove_task(event.id)

                    self._tg.start_soon(finish_item, event)

    def _processor_callback(self, id: str, event: Processing):
        self.progress.update(id, status="Processing[blink]...[/]")

        if event.status == "started":
            match event.task:
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
