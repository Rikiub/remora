from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BasePlaylistEvent, CompletedResult
from remora.models.event.media import MediaEvent


class PlaylistStarted(BasePlaylistEvent):
    status: Literal["started"] = "started"


class PlaylistUpdate(BasePlaylistEvent):
    status: Literal["update"] = "update"


class PlaylistCompleted(BasePlaylistEvent):
    status: Literal["completed"] = "completed"
    result: CompletedResult


class PlaylistCancelled(BasePlaylistEvent):
    status: Literal["cancelled"] = "cancelled"


PlaylistEvent = Annotated[
    PlaylistStarted | PlaylistUpdate | PlaylistCompleted | PlaylistCancelled,
    Field(discriminator="status"),
]

BatchEvent = Annotated[
    PlaylistEvent | MediaEvent,
    Field(discriminator="type"),
]
