from typing import Literal

from remora.models.event._base import BaseEventID, FileEvent
from remora.models.event.process import Processing
from remora.models.event.stream import BatchStreamDownloading
from remora.models.media.item import LazyMedia, Media


class _BaseMedia(BaseEventID):
    type: Literal["media"] = "media"
    media: Media


class MediaStarted(_BaseMedia):
    status: Literal["started"] = "started"
    media: LazyMedia


class MediaExtracting(_BaseMedia):
    status: Literal["extracting"] = "extracting"
    media: LazyMedia


class MediaDownloading(_BaseMedia):
    status: Literal["downloading"] = "downloading"
    progress: BatchStreamDownloading


class MediaProcessing(_BaseMedia):
    status: Literal["processing"] = "processing"
    progress: Processing


class MediaCompleted(_BaseMedia, FileEvent):
    status: Literal["completed"] = "completed"
    result: Literal["success", "partial"]


class MediaSkipped(_BaseMedia, FileEvent):
    status: Literal["skipped"] = "skipped"


class MediaFailed(_BaseMedia):
    status: Literal["failed"] = "failed"
    message: str
    media: LazyMedia | Media


class MediaWarning(_BaseMedia):
    status: Literal["warning"] = "warning"
    message: str


class MediaCancelled(_BaseMedia):
    status: Literal["cancelled"] = "cancelled"
    media: LazyMedia | Media


class MediaEnded(_BaseMedia):
    status: Literal["ended"] = "ended"
    media: LazyMedia


MediaEvent = (
    MediaStarted
    | MediaExtracting
    | MediaDownloading
    | MediaProcessing
    | MediaCompleted
    | MediaSkipped
    | MediaFailed
    | MediaWarning
    | MediaCancelled
    | MediaEnded
)
