from pathlib import Path

from remora.models._base import RemoraModel


class BaseEvent(RemoraModel): ...


class BaseEventID(RemoraModel):
    id: str


class FileEvent(BaseEvent):
    file_path: Path

    @property
    def file_extension(self) -> str:
        return self.file_path.suffix.lstrip(".")
