from typing import Literal

from remora.models.progress._base import BaseStateID
from remora.models.progress.media import MediaState


class _BasePlaylist(BaseStateID):
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


class PlaylistEnded(_BasePlaylist):
    status: Literal["ended"] = "ended"


PlaylistState = (
    PlaylistStarted
    | PlaylistInProgress
    | PlaylistCompleted
    | PlaylistCancelled
    | PlaylistEnded
)
BatchState = PlaylistState | MediaState
