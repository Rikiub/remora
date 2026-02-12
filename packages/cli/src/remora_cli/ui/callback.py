from dataclasses import dataclass

import anyio
from anyio.abc import TaskGroup
from loguru import logger
from remora.models.content.media import LazyMedia
from remora.models.progress.list import ReceivedState
from remora.models.progress.processor import ProcessingState
from remora_cli.ui.bar import DownloadProgress
from rich.progress import TaskID


@dataclass(slots=True)
class Task:
    task_id: TaskID
    id: str
    name: str


class ProgressCallback:
    def __init__(self, disable: bool = False):
        self.disable = disable
        self.progress = DownloadProgress(disable)
        self.tasks: dict[str, Task] = {}

        self._tg: TaskGroup | None = None
        self._exit_stack = anyio.create_task_group()

    async def playlist_callback(self, state: ReceivedState):
        if self.disable:
            return

        if state.type == "playlist":
            match state.status:
                case "started":
                    self.progress.counter.reset(total=state.total)
                case "update":
                    self.progress.counter.update(completed=state.completed)
                case "completed":
                    if state.reason == "success":
                        logger.info("✅ Download Finished.")
                    elif state.reason == "cancelled":
                        logger.warning("❗ Download cancelled.")

        elif state.type == "media":
            if state.status == "resolving":
                task = self.tasks[state.id] = Task(
                    task_id=self.progress.add_task(
                        description="",
                        status="",
                        step="",
                    ),
                    id=state.id,
                    name=self._media_display_name(state.media),
                )

                self.progress.update(
                    task.task_id,
                    description=task.name or "Extracting[blink]...[/]",
                    status="Extracting[blink]...[/]",
                )
                return

            task = self.tasks[state.id]

            match state.status:
                case "resolved":
                    new_name = self._media_display_name(state.media)
                    self.tasks[state.id].name = new_name

                    self.progress.update(
                        task.task_id,
                        description=new_name,
                        status="Ready",
                    )
                case "downloading":
                    self.progress.update(
                        task.task_id,
                        completed=state.downloaded_bytes,
                        total=state.total_bytes,
                        status="Downloading",
                    )
                case "processing":
                    self.processor_callback(state, task)
                case "warning":
                    logger.warning(self.fmt_log(task, f"Warning: {state.message}", "⚠️"))
                case "completed":
                    if state.reason == "success":
                        logger.info(self.fmt_log(task, "Completed", "☑️"))
                        self.progress.update(task.task_id, status="Completed")
                    elif state.reason == "incomplete":
                        logger.warning(self.fmt_log(task, "Completed with errors", "⚠️"))
                        self.progress.update(task.task_id, status="Completed")
                    elif state.reason == "skipped":
                        logger.info(
                            self.fmt_log(
                                task,
                                f'Skipped (Exists as "{state.extension}")',
                                "🔄",
                            )
                        )
                        self.progress.update(task.task_id, status="Skipped")
                    elif state.reason == "failed":
                        logger.error(self.fmt_log(task, "Download failed", "❌"))
                        self.progress.update(task.task_id, status="Error")

                    if self._tg:
                        self._tg.start_soon(self._finish_item, state.id)

    async def _finish_item(self, id: str):
        await anyio.sleep(1.0)

        item = self.tasks.pop(id)
        self.progress.remove_task(item.task_id)

    def processor_callback(self, state: ProcessingState, task: Task):
        match state.processor:
            case "convert_audio":
                if state.stage == "started":
                    self.progress.update(
                        task.task_id,
                        status="Converting[blink]...[/]",
                    )
            case "merge_formats":
                if state.stage == "started":
                    self.progress.update(
                        task.task_id,
                        status="Merging[blink]...[/]",
                    )
            case _:
                self.progress.update(
                    task.task_id,
                    status="Processing[blink]...[/]",
                )

    def fmt_log(
        self,
        task: Task,
        text: str,
        prefix: str = "  ",
    ) -> str:
        return f'   {prefix} "{task.name}": {text}'

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
