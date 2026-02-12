from remora_cli.ui.rich import CONSOLE
from rich.console import Group, RenderableType
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TotalFileSizeColumn,
)
from rich.table import Column


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
            FileSizeColumn(),
            TextColumn("/"),
            TotalFileSizeColumn(),
            transient=True,
            expand=True,
            disable=disable,
            console=CONSOLE,
        )
        self.tasks: dict[str, TaskID] = {}

    def add_task(self, id: str, description: str, status: str):
        task_id = self._progress.add_task(description, status=status)
        self.tasks[id] = task_id

    def remove_task(self, id: str):
        self._progress.remove_task(self.tasks[id])

    def update(
        self,
        id: str,
        description: str | None = None,
        status: str | None = None,
        completed: float | None = None,
        total: float | None = None,
    ):
        self._progress.update(
            self.tasks[id],
            description=description,
            status=status,
            completed=completed,
            total=total,
        )

    def get_renderable(self) -> RenderableType:
        return Group(self.counter, self._progress)

    def start(self):
        self._progress.start()

    def stop(self):
        self._progress.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
