from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseMediaEvent, CompletedResult, FileEvent
from remora.models.event.process import (
    ProcessEvent,
    Processing,  # noqa: F401
)
from remora.models.event.stream import DownloadingStream
from remora.models.media.item import LazyMedia


class Extracting(BaseMediaEvent):
    status: Literal["extracting"] = "extracting"
    media: LazyMedia  # type: ignore


class Preparing(BaseMediaEvent):
    status: Literal["preparing"] = "preparing"


class Downloading(DownloadingStream, BaseMediaEvent): ...


class Warning(BaseMediaEvent):
    status: Literal["warning"] = "warning"
    message: str


class Completed(BaseMediaEvent, FileEvent):
    status: Literal["completed"] = "completed"
    result: CompletedResult | Literal["duplicate"]


class Failed(BaseMediaEvent):
    status: Literal["failed"] = "failed"
    error: str


class Cancelled(BaseMediaEvent):
    status: Literal["cancelled"] = "cancelled"


MediaEvent = Annotated[
    Extracting
    | Preparing
    | Downloading
    | ProcessEvent
    | Warning
    | Completed
    | Failed
    | Cancelled,
    Field(discriminator="status"),
]
