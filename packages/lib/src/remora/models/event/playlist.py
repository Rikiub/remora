from typing import Literal

from remora.models.event._base import BaseEventID
from remora.models.event.media import MediaEvent


class _BasePlaylist(BaseEventID):
    type: Literal["playlist"] = "playlist"

    completed: int
    total: int


class PlaylistStarted(_BasePlaylist):
    status: Literal["started"] = "started"


class PlaylistInProgress(_BasePlaylist):
    status: Literal["in_progress"] = "in_progress"


class PlaylistCompleted(_BasePlaylist):
    status: Literal["completed"] = "completed"
    result: Literal["success", "partial"]


class PlaylistCancelled(_BasePlaylist):
    status: Literal["cancelled"] = "cancelled"


PlaylistEvent = (
    PlaylistStarted | PlaylistInProgress | PlaylistCompleted | PlaylistCancelled
)
BatchEvent = PlaylistEvent | MediaEvent
