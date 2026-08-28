from rich.console import Group, RenderableType
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
)
from rich.table import Column

from remora_cli.ui.rich import CONSOLE


class CounterProgress:
    def __init__(
        self,
        total: int = 1,
        disable: bool = False,
        visible: bool = True,
    ) -> None:
        self._progress = Progress(
            TextColumn("Total:"),
            MofNCompleteColumn(),
            transient=True,
            expand=False,
            disable=disable,
            console=CONSOLE,
        )
        self._task_id = self._progress.add_task(
            "",
            visible=visible,
            completed=0,
            total=total,
        )

    def update(
        self,
        completed: float = 0,
        total: float | None = None,
        visible: bool | None = None,
    ):
        self._progress.update(
            self._task_id,
            completed=completed,
            total=total,
            visible=visible,
        )

    def reset(
        self,
        completed: int = 0,
        total: int | None = None,
        visible: bool | None = None,
    ):
        self._progress.reset(
            self._task_id,
            completed=completed,
            total=total,
            visible=visible,
        )

    def __rich__(self) -> RenderableType:
        return self._progress.get_renderable()


class DownloadProgress:
    """Start and render progress bar."""

    def __init__(self, disable: bool = False) -> None:
        self.disable = disable
        self.counter = CounterProgress(disable=disable)
        self._progress = Progress(
            TextColumn(
                "{task.description}",
                table_column=Column(ratio=5, no_wrap=True, overflow="ellipsis"),
            ),
            TextColumn(
                "[turquoise2]{task.fields[status]}",
                table_column=Column(ratio=2, no_wrap=True),
            ),
            BarColumn(table_column=Column(justify="full", ratio=4)),
            DownloadColumn(),
            disable=disable,
            transient=True,
            expand=True,
            console=CONSOLE,
        )
        self._live = Live(
            renderable=Group(self.counter, self._progress),
            console=CONSOLE,
        )
        self.tasks: dict[str, TaskID] = {}

    def update(
        self,
        id: str,
        description: str | None = None,
        status: str | None = None,
        completed: float | None = None,
        total: float | None = None,
    ):
        if id in self.tasks:
            self._progress.update(
                self.tasks[id],
                description=description,
                status=status,
                completed=completed,
                total=total,
            )
        else:
            self.tasks[id] = self._progress.add_task(
                description=description or "",
                status=status,
                completed=int(completed or 0),
                total=total,
            )

    def remove_task(self, id: str):
        task_id = self.tasks.pop(id)
        self._progress.remove_task(task_id)

    def start(self):
        if not self.disable:
            self._live.start()

    def stop(self):
        if not self.disable:
            self._live.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
