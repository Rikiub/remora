from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import (
    BaseEventID,
    CompletedResult,
    FileEvent,
)
from remora.models.event.process import ProcessEvent
from remora.models.event.stream import BatchStreamDownloading
from remora.models.media.item import LazyMedia, Media


class BaseMediaEvent(BaseEventID):
    type: Literal["media"] = "media"
    media: Media


class MediaExtracting(BaseMediaEvent):
    status: Literal["extracting"] = "extracting"
    media: LazyMedia  # type: ignore


class MediaDownloading(BaseMediaEvent):
    status: Literal["downloading"] = "downloading"
    progress: BatchStreamDownloading


class MediaProcessing(BaseMediaEvent):
    status: Literal["processing"] = "processing"
    progress: ProcessEvent


class MediaCompleted(BaseMediaEvent, FileEvent):
    status: Literal["completed"] = "completed"
    result: CompletedResult | Literal["duplicate"]


class MediaFailed(BaseMediaEvent):
    status: Literal["failed"] = "failed"
    message: str


class MediaWarning(BaseMediaEvent):
    status: Literal["warning"] = "warning"
    message: str


class MediaCancelled(BaseMediaEvent):
    status: Literal["cancelled"] = "cancelled"
    media: LazyMedia | Media  # type: ignore


MediaEvent = Annotated[
    MediaExtracting
    | MediaDownloading
    | MediaProcessing
    | MediaCompleted
    | MediaFailed
    | MediaWarning
    | MediaCancelled,
    Field(discriminator="status"),
]
