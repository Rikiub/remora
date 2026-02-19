from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from remora.models.media.item import Media


class BaseEvent(BaseModel): ...


class BaseEventID(BaseModel):
    id: str


class BaseMediaEvent(BaseEventID):
    type: Literal["media"] = "media"
    media: Media


class BasePlaylistEvent(BaseEventID):
    type: Literal["playlist"] = "playlist"

    completed: int
    total: int


class FileEvent(BaseEvent):
    file_path: Path

    @property
    def file_extension(self) -> str:
        return self.file_path.suffix.lstrip(".")


CompletedResult = Literal["success", "partial"]
