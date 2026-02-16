from typing import Annotated, Literal

from pydantic import Field

from remora.models.event.base import BaseEvent, FileEvent


class DownloadingStream(BaseEvent):
    status: Literal["downloading"] = "downloading"

    downloaded: float = 0
    total: float = 0

    speed: float = 0
    elapsed: float = 0


class FinishedStream(FileEvent):
    status: Literal["finished"] = "finished"


StreamEvent = Annotated[
    DownloadingStream | FinishedStream,
    Field(discriminator="status"),
]
