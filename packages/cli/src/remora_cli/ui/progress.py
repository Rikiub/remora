import anyio
from anyio.abc import TaskGroup
from loguru import logger

from remora.models.event.media import (
    MediaCompleted,
    MediaDownloading,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaWarning,
)
from remora.models.event.playlist import (
    BatchEvent,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
)
from remora.models.event.process import Processing
from remora.models.media.item import LazyMedia
from remora_cli.ui.rich_progress import DownloadProgress


class ProgressCallback:
    def __init__(self, disable: bool = False):
        self.disable = disable
        self.progress = DownloadProgress(disable)

        self._tg: TaskGroup | None = None
        self._exit_stack = anyio.create_task_group()

    async def playlist_callback(self, event: BatchEvent):
        if self.disable:
            return

        name = ""

        with logger.contextualize(media_title=name):
            match event:
                # Playlist
                case PlaylistStarted():
                    self.progress.counter.reset(total=event.total)
                case PlaylistInProgress():
                    self.progress.counter.update(completed=event.completed)
                case PlaylistCancelled():
                    logger.warning("Download cancelled")

                case PlaylistCompleted(result="success"):
                    logger.success("Download completed")
                case PlaylistCompleted(result="partial"):
                    logger.success("Download completed (Some items failed)")

                # Media
                case MediaExtracting():
                    self.progress.add_task(
                        event.id,
                        description=name or "Extracting[blink]...[/]",
                        status="Extracting[blink]...[/]",
                    )
                case MediaDownloading():
                    self.progress.update(
                        event.id,
                        description=name,
                        status="Downloading",
                        completed=event.progress.downloaded_bytes,
                        total=event.progress.total_bytes,
                    )
                case MediaProcessing():
                    self.processor_callback(event.id, event.progress)
                case MediaWarning():
                    logger.warning("Warning: {}", event.message)
                case MediaFailed():
                    logger.error("Download failed: {}", event.message)
                    self.progress.update(event.id, status="Error")
                case MediaCompleted():
                    match event.result:
                        case "success":
                            logger.success("Completed")
                            self.progress.update(event.id, status="Completed")
                        case "partial":
                            logger.success("Completed (Some data missed)")
                            self.progress.update(event.id, status="Completed")
                        case "duplicate":
                            logger.success(
                                'Skipped (Exists as "{file_extension}")',
                                file_extension=event.file_extension,
                                icon="🔄",
                            )
                            self.progress.update(event.id, status="Skipped")

                    if self._tg:
                        self._tg.start_soon(self._finish_item, event)

    async def _finish_item(self, event: BatchEvent):
        await anyio.sleep(1.0)
        self.progress.remove_task(event.id)

    def processor_callback(self, id: str, event: Processing):
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

    async def __aenter__(self):
        self._tg = await self._exit_stack.__aenter__()
        self.progress.start()
        return self

    async def __aexit__(self, *args):
        await self._exit_stack.__aexit__(*args)
        self.progress.stop()
