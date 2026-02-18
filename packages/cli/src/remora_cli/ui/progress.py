import anyio
from anyio.abc import TaskGroup
from loguru import logger

from remora.models.event.playlist import BatchEvent
from remora.models.event.process import ProcessEvent
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

        if event.type == "playlist":
            match event.status:
                case "started":
                    self.progress.counter.reset(total=event.total)
                case "update":
                    self.progress.counter.update(completed=event.completed)
                case "finished":
                    if event.result == "success":
                        logger.success("Download completed")
                    elif event.result == "incomplete":
                        logger.warning("Completed with errors")
                    elif event.result == "cancelled":
                        logger.warning("Download cancelled")

        elif event.type == "media":
            name = self._media_display_name(event.media)

            with logger.contextualize(media_title=name):
                match event.status:
                    case "resolving":
                        self.progress.add_task(
                            event.id,
                            description=name or "Extracting[blink]...[/]",
                            status="Extracting[blink]...[/]",
                        )
                    case "resolved":
                        self.progress.update(
                            event.id,
                            description=name,
                            status="Preparing[blink]...[/]",
                        )
                    case "downloading":
                        self.progress.update(
                            event.id,
                            status="Downloading",
                            completed=event.downloaded,
                            total=event.total,
                        )
                    case "processing":
                        self.processor_callback(event)
                    case "warning":
                        logger.warning("Warning: {message}", message=event.message)
                    case "finished":
                        if event.result == "success":
                            logger.success("Completed")
                            self.progress.update(event.id, status="Completed")
                        elif event.result == "incomplete":
                            logger.warning("Completed with errors")
                            self.progress.update(event.id, status="Completed")
                        elif event.result == "skipped":
                            logger.success(
                                'Skipped (Exists as "{extension}")',
                                extension=event.extension,
                                icon="🔄",
                            )
                            self.progress.update(event.id, status="Skipped")
                        elif event.result == "failed":
                            logger.warning("Download failed")
                            self.progress.update(event.id, status="Error")

                        if self._tg:
                            self._tg.start_soon(self._finish_item, event)

    async def _finish_item(self, event: BatchEvent):
        await anyio.sleep(1.0)
        self.progress.remove_task(event.id)

    def processor_callback(self, event: ProcessEvent):
        match event.task:
            case "convert_audio":
                if event.step == "started":
                    self.progress.update(
                        event.id,
                        status="Converting[blink]...[/]",
                    )
            case "merge_formats":
                if event.step == "started":
                    self.progress.update(
                        event.id,
                        status="Merging[blink]...[/]",
                    )
            case _:
                self.progress.update(
                    event.id,
                    status="Processing[blink]...[/]",
                )

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
