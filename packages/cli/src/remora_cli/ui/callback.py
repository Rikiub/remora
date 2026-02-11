from dataclasses import dataclass

import anyio
from loguru import logger
from remora.models.content.media import LazyMedia
from remora.models.progress.list import PlaylistDownloadState
from remora.models.progress.media import MediaDownloadState
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
        self.ids: dict[str, Task] = {}

    async def playlist_callback(self, state: PlaylistDownloadState):
        if self.disable:
            return

        if state.type == "playlist":
            match state.stage:
                case "started":
                    self.progress.counter.reset(total=state.total)
                    self.progress.start()
                case "update":
                    self.progress.counter.update(completed=state.completed)
                case "completed":
                    self.progress.stop()

        elif state.type == "media":
            match state.status:
                case "resolving":
                    item = self.ids[state.id] = Task(
                        task_id=self.progress.add_task(
                            description="",
                            status="",
                            step="",
                        ),
                        id=state.id,
                        name=self._media_display_name(state.media),
                    )

                    self.progress.update(
                        item.task_id,
                        description=item.name or "Extracting[blink]...[/]",
                        status="Extracting[blink]...[/]",
                    )
                case "resolved":
                    new_name = self._media_display_name(state.media)
                    self.ids[state.id].name = new_name

                    self.progress.update(
                        self.get(state).task_id,
                        description=new_name,
                        status="Ready",
                    )
                case "downloading":
                    self.progress.update(
                        self.get(state).task_id,
                        completed=state.downloaded_bytes,
                        total=state.total_bytes,
                        status="Downloading",
                    )
                case "processing":
                    self.processor_callback(state)
                case "warning":
                    logger.warning(
                        self.fmt_log(state, f"Warning: {state.message}", "⚠️")
                    )
                case "completed":
                    task = self.get(state)

                    if state.reason == "success":
                        logger.info(self.fmt_log(state, "Completed", "☑️"))
                        self.progress.update(task.task_id, status="Completed")
                    elif state.reason == "incomplete":
                        logger.warning(
                            self.fmt_log(state, "Completed with errors", "⚠️")
                        )
                        self.progress.update(task.task_id, status="Completed")
                    elif state.reason == "skipped":
                        logger.info(
                            self.fmt_log(
                                state,
                                f'Skipped (Exists as "{state.extension}")',
                                "🔄",
                            )
                        )
                        self.progress.update(task.task_id, status="Skipped")
                    elif state.reason == "failed":
                        logger.error(self.fmt_log(state, "Download failed", "❌"))
                        self.progress.update(task.task_id, status="Error")

                    self.progress.counter.advance()
                    # await anyio.sleep(1.0)
                    self.progress.remove_task(task.task_id)

    def processor_callback(self, state: ProcessingState):
        match state.processor:
            case "convert_audio":
                if state.stage == "started":
                    self.progress.update(
                        self.get(state).task_id,
                        status="Converting[blink]...[/]",
                    )
            case "merge_formats":
                if state.stage == "started":
                    self.progress.update(
                        self.get(state).task_id,
                        status="Merging[blink]...[/]",
                    )
            case _:
                self.progress.update(
                    self.get(state).task_id,
                    status="Processing[blink]...[/]",
                )

    def get(self, state: MediaDownloadState):
        return self.ids[state.id]

    def fmt_log(
        self,
        state: MediaDownloadState,
        text: str,
        prefix: str = "  ",
    ) -> str:
        task = self.get(state)
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
        self.progress.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
