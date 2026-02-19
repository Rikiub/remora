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


class Resolving(BaseMediaEvent):
    status: Literal["resolving"] = "resolving"
    media: LazyMedia  # type: ignore


class Resolved(BaseMediaEvent):
    status: Literal["resolved"] = "resolved"


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
    Resolving
    | Resolved
    | Downloading
    | ProcessEvent
    | Warning
    | Completed
    | Failed
    | Cancelled,
    Field(discriminator="status"),
]
