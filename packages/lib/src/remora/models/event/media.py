from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from remora.models.content.media import LazyMedia
from remora.models.event.base import BaseMediaEvent, FileEvent
from remora.models.event.processor import Processing
from remora.models.event.stream import DownloadingStream


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


class Finished(BaseMediaEvent, FileEvent):
    status: Literal["finished"] = "finished"
    result: Literal["success", "incomplete", "skipped", "failed"]


MediaEvent = Annotated[
    Resolving | Resolved | Downloading | Retrying | Processing | Warning | Finished,
    Field(discriminator="status"),
]
