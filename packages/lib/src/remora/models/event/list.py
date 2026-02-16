from typing import Annotated, Literal

from pydantic import Field

from remora.models.event.base import BasePlaylistEvent


class PlaylistUpdate(BasePlaylistEvent):
    status: Literal["started", "update"]

    completed: int
    total: int


class FinishedPlaylist(PlaylistUpdate):
    status: Literal["finished"] = "finished"  # type: ignore
    result: Literal["success", "incomplete", "cancelled"]


PlaylistEvent = Annotated[
    PlaylistUpdate | FinishedPlaylist,
    Field(discriminator="status"),
]
