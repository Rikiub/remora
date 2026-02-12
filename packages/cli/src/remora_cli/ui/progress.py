import anyio
from anyio.abc import TaskGroup
from loguru import logger
from remora.models.content.media import LazyMedia
from remora.models.event.main import DownloadEvent
from remora.models.event.processor import Processing
from remora_cli.ui.rich_progress import DownloadProgress


class ProgressCallback:
    def __init__(self, disable: bool = False):
        self.disable = disable
        self.progress = DownloadProgress(disable)

        self._tg: TaskGroup | None = None
        self._exit_stack = anyio.create_task_group()

    async def playlist_callback(self, event: DownloadEvent):
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
                        logger.info("✅ Download completed")
                    elif event.result == "incomplete":
                        logger.warning("⚠️ Completed with errors")
                    elif event.result == "cancelled":
                        logger.warning("❗ Download cancelled")

        elif event.type == "media":
            name = self._media_display_name(event.media)

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
                        status="Ready",
                    )
                case "downloading":
                    self.progress.update(
                        event.id,
                        status="Downloading",
                        completed=event.downloaded_bytes,
                        total=event.total_bytes,
                    )
                case "processing":
                    self.processor_callback(event)
                case "warning":
                    logger.warning(self.fmt_log(name, f"Warning: {event.message}", "⚠️"))
                case "finished":
                    if event.result == "success":
                        logger.info(self.fmt_log(name, "Completed", "☑️"))
                        self.progress.update(event.id, status="Completed")
                    elif event.result == "incomplete":
                        logger.warning(self.fmt_log(name, "Completed with errors", "⚠️"))
                        self.progress.update(event.id, status="Completed")
                    elif event.result == "skipped":
                        logger.info(
                            self.fmt_log(
                                name,
                                f'Skipped (Exists as "{event.extension}")',
                                "🔄",
                            )
                        )
                        self.progress.update(event.id, status="Skipped")
                    elif event.result == "failed":
                        logger.error(self.fmt_log(name, "Download failed", "❌"))
                        self.progress.update(event.id, status="Error")

                    if self._tg:
                        self._tg.start_soon(self._finish_item, event)

    async def _finish_item(self, event: DownloadEvent):
        await anyio.sleep(1.0)
        self.progress.remove_task(event.id)

    def processor_callback(self, event: Processing):
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

    def fmt_log(
        self,
        name: str,
        content: str,
        prefix: str = "  ",
    ) -> str:
        return f'   {prefix} "{name}": {content}'

    def _media_display_name(self, media: LazyMedia) -> str:
        """Get pretty representation of media name."""

        if media.is_music and media.uploader and media.title:
            return media.title + " - " + media.uploader
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
