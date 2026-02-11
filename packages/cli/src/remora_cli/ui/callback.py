import time
from dataclasses import dataclass

from loguru import logger
from remora.models.content.media import LazyMedia
from remora.models.progress.list import PlaylistDownloadState
from remora.models.progress.media import MediaDownloadState
from remora.models.progress.processor import ProcessingState
from rich.progress import TaskID

from remora_cli.ui.bar import DownloadProgress


@dataclass(slots=True)
class Task:
    task_id: TaskID
    id: str
    name: str


class ProgressCallback(DownloadProgress):
    def __init__(self, disable: bool = False) -> None:
        super().__init__(disable)
        self.ids: dict[str, Task] = {}

    async def callback_media(self, progress: MediaDownloadState):
        match progress.status:
            case "resolving":
                item = self.ids[progress.id] = Task(
                    task_id=self.add_task(
                        description="",
                        status="",
                        step="",
                    ),
                    id=progress.id,
                    name=self._media_display_name(progress.media),
                )

                self.update(
                    item.task_id,
                    description=item.name or "Extracting[blink]...[/]",
                    status="Extracting[blink]...[/]",
                )
            case "resolved":
                new_name = self._media_display_name(progress.media)
                self.ids[progress.id].name = new_name

                self.update(
                    self.get(progress).task_id,
                    description=new_name,
                    status="Ready",
                )
            case "downloading":
                self.update(
                    self.get(progress).task_id,
                    completed=progress.downloaded_bytes,
                    total=progress.total_bytes,
                    status="Downloading",
                )
            case "processing":
                await self.processor_callback(progress)
            case "warning":
                logger.warning(
                    self.fmt_log(progress, f"Warning: {progress.message}", "⚠️")
                )
            case "completed":
                task = self.get(progress)

                if progress.reason == "success":
                    logger.info(self.fmt_log(progress, "Completed", "☑️"))
                    self.update(task.task_id, status="Completed")
                elif progress.reason == "incomplete":
                    logger.warning(self.fmt_log(progress, "Completed with errors", "⚠️"))
                    self.update(task.task_id, status="Completed")
                elif progress.reason == "skipped":
                    logger.info(
                        self.fmt_log(
                            progress,
                            f'Skipped (Exists as "{progress.extension}")',
                            "🔄",
                        )
                    )
                    self.update(task.task_id, status="Skipped")
                elif progress.reason == "failed":
                    logger.error(self.fmt_log(progress, "Download failed", "❌"))
                    self.update(task.task_id, status="Error")

                self.counter.advance()
                time.sleep(1.0)
                self.remove_task(self.get(progress).task_id)

    async def callback_playlist(self, progress: PlaylistDownloadState):
        match progress.stage:
            case "started":
                self.counter.reset(total=progress.total)
                self.start()
            case "update":
                self.counter.update(completed=progress.completed)
            case "completed":
                self.stop()

    async def processor_callback(self, progress: ProcessingState):
        match progress.processor:
            case "convert_audio":
                if progress.stage == "started":
                    self.update(
                        self.get(progress).task_id,
                        status="Converting[blink]...[/]",
                    )
            case "merge_formats":
                if progress.stage == "started":
                    self.update(
                        self.get(progress).task_id,
                        status="Merging[blink]...[/]",
                    )
            case _:
                self.update(
                    self.get(progress).task_id,
                    status="Processing[blink]...[/]",
                )

    def get(self, progress: MediaDownloadState):
        return self.ids[progress.id]

    def fmt_log(
        self, progress: MediaDownloadState, text: str, prefix: str = "  "
    ) -> str:
        task = self.get(progress)
        return f'   {prefix} "{task.name}": {text}'

    def _media_display_name(self, media: LazyMedia) -> str:
        """Get pretty representation of media name."""

        if media.is_music and media.uploader and media.title:
            return media.title + " - " + media.uploader
        elif media.title:
            return media.title
        else:
            return ""
