import anyio
from anyio.abc import TaskGroup
from loguru import logger

from remora.models.event.enum import CompletedResult, EventStatus, EventType
from remora.models.event.playlist import BatchEvent
from remora.models.event.process import ProcessEvent, ProcessorTask
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

        if event.type == EventType.PLAYLIST:
            match event.status:
                case EventStatus.STARTED:
                    self.progress.counter.reset(total=event.total)
                case EventStatus.IN_PROGRESS:
                    self.progress.counter.update(completed=event.completed)
                case EventStatus.COMPLETED:
                    match event.result:
                        case CompletedResult.SUCCESS:
                            logger.success("Download completed")
                        case CompletedResult.PARTIAL:
                            logger.success("Download completed (Some items failed)")
                case EventStatus.CANCELLED:
                    logger.warning("Download cancelled")

        elif event.type == EventType.MEDIA:
            name = self._media_display_name(event.media)

            with logger.contextualize(media_title=name):
                match event.status:
                    case EventStatus.EXTRACTING:
                        self.progress.add_task(
                            event.id,
                            description=name or "Extracting[blink]...[/]",
                            status="Extracting[blink]...[/]",
                        )
                    case EventStatus.DOWNLOADING:
                        self.progress.update(
                            event.id,
                            description=name,
                            status="Downloading",
                            completed=event.progress.downloaded_bytes,
                            total=event.progress.total_bytes,
                        )
                    case EventStatus.PROCESSING:
                        self.processor_callback(event.id, event.progress)
                    case EventStatus.WARNING:
                        logger.warning("Warning: {}", event.message)
                    case EventStatus.FAILED:
                        logger.error("Download failed: {}", event.message)
                        self.progress.update(event.id, status="Error")
                    case EventStatus.COMPLETED:
                        match event.result:
                            case CompletedResult.SUCCESS:
                                logger.success("Completed")
                                self.progress.update(event.id, status="Completed")
                            case CompletedResult.PARTIAL:
                                logger.success("Completed (Some data missed)")
                                self.progress.update(event.id, status="Completed")
                            case CompletedResult.DUPLICATE:
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

    def processor_callback(self, id: str, event: ProcessEvent):
        self.progress.update(id, status="Processing[blink]...[/]")

        if event.status == EventStatus.STARTED:
            match event.task:
                case ProcessorTask.CONVERT_AUDIO:
                    self.progress.update(id, status="Converting[blink]...[/]")
                case ProcessorTask.MERGE_STREAMS:
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
