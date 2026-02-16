from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from remora.models.content.media import Media


class BaseEvent(BaseModel): ...


class EventID(BaseModel):
    id: str


class BaseMediaEvent(EventID):
    type: Literal["media"] = "media"
    media: Media


class BasePlaylistEvent(EventID):
    type: Literal["playlist"] = "playlist"


class FileEvent(BaseEvent):
    filepath: Path

    @property
    def extension(self) -> str:
        return self.filepath.suffix.lstrip(".")
