from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseEventID, FileEvent
from remora.models.event.enum import CompletedResult, EventStatus, EventType
from remora.models.event.process import ProcessEvent
from remora.models.event.stream import BatchStreamDownloading
from remora.models.media.item import LazyMedia, Media


class BaseMediaEvent(BaseEventID):
    type: Literal[EventType.MEDIA, "media"] = EventType.MEDIA
    media: Media


class MediaExtracting(BaseMediaEvent):
    status: Literal[EventStatus.EXTRACTING, "extracting"] = EventStatus.EXTRACTING
    media: LazyMedia  # type: ignore


class MediaDownloading(BaseMediaEvent):
    status: Literal[EventStatus.DOWNLOADING, "downloading"] = EventStatus.DOWNLOADING
    progress: BatchStreamDownloading


class MediaProcessing(BaseMediaEvent):
    status: Literal[EventStatus.PROCESSING, "processing"] = EventStatus.PROCESSING
    progress: ProcessEvent


class MediaCompleted(BaseMediaEvent, FileEvent):
    status: Literal[EventStatus.COMPLETED, "completed"] = EventStatus.COMPLETED
    result: Literal[
        CompletedResult.SUCCESS,
        CompletedResult.PARTIAL,
        CompletedResult.DUPLICATE,
        "success",
        "partial",
        "duplicate",
    ]


class MediaFailed(BaseMediaEvent):
    status: Literal[EventStatus.FAILED, "failed"] = EventStatus.FAILED
    message: str


class MediaWarning(BaseMediaEvent):
    status: Literal[EventStatus.WARNING, "warning"] = EventStatus.WARNING
    message: str


class MediaCancelled(BaseMediaEvent):
    status: Literal[EventStatus.CANCELLED, "cancelled"] = EventStatus.CANCELLED
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
