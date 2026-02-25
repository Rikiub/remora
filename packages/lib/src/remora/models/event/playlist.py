from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseEventID
from remora.models.event.enum import CompletedResult, EventStatus, EventType
from remora.models.event.media import MediaEvent


class BasePlaylistEvent(BaseEventID):
    type: Literal[EventType.PLAYLIST, "playlist"] = EventType.PLAYLIST

    completed: int
    total: int


class PlaylistStarted(BasePlaylistEvent):
    status: Literal[EventStatus.STARTED, "started"] = EventStatus.STARTED


class PlaylistInProgress(BasePlaylistEvent):
    status: Literal[EventStatus.IN_PROGRESS, "in_progress"] = EventStatus.IN_PROGRESS


class PlaylistCompleted(BasePlaylistEvent):
    status: Literal[EventStatus.COMPLETED, "completed"] = EventStatus.COMPLETED
    result: Literal[
        CompletedResult.SUCCESS,
        CompletedResult.PARTIAL,
        "success",
        "partial",
    ]


class PlaylistCancelled(BasePlaylistEvent):
    status: Literal[EventStatus.CANCELLED, "cancelled"] = EventStatus.CANCELLED


PlaylistEvent = Annotated[
    PlaylistStarted | PlaylistInProgress | PlaylistCompleted | PlaylistCancelled,
    Field(discriminator="status"),
]

BatchEvent = Annotated[
    PlaylistEvent | MediaEvent,
    Field(discriminator="type"),
]
