from pathlib import Path

from pydantic import BaseModel


class BaseEvent(BaseModel): ...


class BaseEventID(BaseModel):
    id: str


class FileEvent(BaseEvent):
    file_path: Path

    @property
    def file_extension(self) -> str:
        return self.file_path.suffix.lstrip(".")
