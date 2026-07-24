from typing import Literal

from remora.models.event._base import BaseEventID, FileEvent
from remora.models.event.process import Processing
from remora.models.event.stream import BatchStreamDownloading
from remora.models.media.item import LazyMedia, Media


class _BaseMedia(BaseEventID):
    type: Literal["media"] = "media"
    media: Media


class MediaExtracting(_BaseMedia):
    status: Literal["extracting"] = "extracting"
    media: LazyMedia  # type: ignore


class MediaDownloading(_BaseMedia):
    status: Literal["downloading"] = "downloading"
    progress: BatchStreamDownloading


class MediaProcessing(_BaseMedia):
    status: Literal["processing"] = "processing"
    progress: Processing


class MediaCompleted(_BaseMedia, FileEvent):
    status: Literal["completed"] = "completed"
    result: Literal["success", "partial", "duplicate"]


class MediaFailed(_BaseMedia):
    status: Literal["failed"] = "failed"
    message: str


class MediaWarning(_BaseMedia):
    status: Literal["warning"] = "warning"
    message: str


class MediaCancelled(_BaseMedia):
    status: Literal["cancelled"] = "cancelled"
    media: LazyMedia | Media  # type: ignore


MediaEvent = (
    MediaExtracting
    | MediaDownloading
    | MediaProcessing
    | MediaCompleted
    | MediaFailed
    | MediaWarning
    | MediaCancelled
)
