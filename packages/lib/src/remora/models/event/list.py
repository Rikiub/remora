from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BasePlaylistEvent


class PlaylistUpdate(BasePlaylistEvent):
    status: Literal["started", "update"]

    completed: int
    total: int


FinishedPlaylistResult = Literal["success", "incomplete", "cancelled"]


class FinishedPlaylist(PlaylistUpdate):
    status: Literal["finished"] = "finished"  # type: ignore
    result: FinishedPlaylistResult


PlaylistEvent = Annotated[
    PlaylistUpdate | FinishedPlaylist,
    Field(discriminator="status"),
]
