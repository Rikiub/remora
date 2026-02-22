from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseEventID, CompletedResult
from remora.models.event.media import MediaEvent


class BasePlaylistEvent(BaseEventID):
    type: Literal["playlist"] = "playlist"

    completed: int
    total: int


class PlaylistStarted(BasePlaylistEvent):
    status: Literal["started"] = "started"


class PlaylistInProgress(BasePlaylistEvent):
    status: Literal["in_progress"] = "in_progress"


class PlaylistCompleted(BasePlaylistEvent):
    status: Literal["completed"] = "completed"
    result: CompletedResult


class PlaylistCancelled(BasePlaylistEvent):
    status: Literal["cancelled"] = "cancelled"


PlaylistEvent = Annotated[
    PlaylistStarted | PlaylistInProgress | PlaylistCompleted | PlaylistCancelled,
    Field(discriminator="status"),
]

BatchEvent = Annotated[
    PlaylistEvent | MediaEvent,
    Field(discriminator="type"),
]
