from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from remora.models.content.media import Media


class BaseEvent(BaseModel): ...


class EventId(BaseModel):
    id: str


class BaseMediaEvent(EventId):
    type: Literal["media"] = "media"
    media: Media


class BasePlaylistEvent(EventId):
    type: Literal["playlist"] = "playlist"


class FileEvent(BaseEvent):
    filepath: Path

    @property
    def extension(self) -> str:
        return self.filepath.suffix.lstrip(".")
