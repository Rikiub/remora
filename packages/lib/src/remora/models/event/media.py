from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseMediaEvent, FileEvent
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


class Retrying(BaseMediaEvent):
    status: Literal["retrying"] = "retrying"
    result: Literal["stale_cache"]


class Downloading(DownloadingStream, BaseMediaEvent): ...


class Warning(BaseMediaEvent):
    status: Literal["warning"] = "warning"
    message: str


FinishedResult = Literal["success", "incomplete", "skipped", "failed"]


class Finished(BaseMediaEvent, FileEvent):
    status: Literal["finished"] = "finished"
    result: FinishedResult


MediaEvent = Annotated[
    Resolving | Resolved | Downloading | Retrying | ProcessEvent | Warning | Finished,
    Field(discriminator="status"),
]
