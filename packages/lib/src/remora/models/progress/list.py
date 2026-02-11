from typing import Annotated, Literal

from pydantic import BaseModel, Field
from remora.models.progress.base import StageType
from remora.models.progress.media import MediaDownloadState


class PlaylistState(BaseModel):
    type: Literal["playlist"] = "playlist"
    stage: Literal[StageType, "update"]
    id: str

    completed: int
    total: int


PlaylistDownloadState = Annotated[
    PlaylistState | MediaDownloadState,
    Field(discriminator="type"),
]
