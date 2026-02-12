from typing import Annotated, Literal

from pydantic import BaseModel, Field
from remora.models.progress.media import MediaDownloadState


class PlaylistState(BaseModel):
    type: Literal["playlist"] = "playlist"
    status: Literal["started", "update"]
    id: str

    completed: int
    total: int


class CompletedPlaylistState(PlaylistState):
    status: Literal["completed"] = "completed"  # type: ignore
    reason: Literal["success", "cancelled"]


PlaylistDownloadState = Annotated[
    PlaylistState | CompletedPlaylistState,
    Field(discriminator="status"),
]

ReceivedState = Annotated[
    PlaylistDownloadState | MediaDownloadState,
    Field(discriminator="type"),
]
