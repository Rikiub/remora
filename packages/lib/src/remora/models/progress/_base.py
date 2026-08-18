from pathlib import Path

from pydantic import computed_field

from remora.models._base import RemoraModel


class BaseState(RemoraModel): ...


class BaseStateID(RemoraModel):
    id: str


class FileState(BaseState):
    file_path: Path

    @computed_field
    @property
    def file_extension(self) -> str:
        return self.file_path.suffix.lstrip(".")
