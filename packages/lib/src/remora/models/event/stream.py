from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseEvent, FileEvent


class DownloadingStream(BaseEvent):
    status: Literal["downloading"] = "downloading"

    downloaded: float = 0
    total: float = 0

    speed: float = 0
    elapsed: float = 0


class CompletedStream(FileEvent):
    status: Literal["completed"] = "completed"


StreamEvent = Annotated[
    DownloadingStream | CompletedStream,
    Field(discriminator="status"),
]
