from typing import Literal

from remora.models.media.item import LazyMedia, Media
from remora.models.progress._base import BaseStateID, FileState
from remora.models.progress.process import Processing
from remora.models.progress.stream import BatchStreamDownloading

__all__ = [
    "MediaCompleted",
    "MediaDownloading",
    "MediaEnded",
    "MediaExtracting",
    "MediaFailed",
    "MediaProcessing",
    "MediaSkipped",
    "MediaState",
    "MediaWaiting",
    "MediaWarning",
]


class _BaseMedia(BaseStateID):
    type: Literal["media"] = "media"
    media: Media


class MediaWaiting(_BaseMedia):
    status: Literal["waiting"] = "waiting"
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


class MediaCompleted(_BaseMedia, FileState):
    status: Literal["completed"] = "completed"
    result: Literal["success", "partial"]


class MediaSkipped(_BaseMedia, FileState):
    status: Literal["skipped"] = "skipped"


class MediaFailed(_BaseMedia):
    status: Literal["failed"] = "failed"
    message: str
    media: LazyMedia | Media


class MediaWarning(_BaseMedia):
    status: Literal["warning"] = "warning"
    message: str


class MediaEnded(_BaseMedia):
    status: Literal["ended"] = "ended"
    media: LazyMedia


MediaState = (
    MediaWaiting
    | MediaExtracting
    | MediaDownloading
    | MediaProcessing
    | MediaCompleted
    | MediaSkipped
    | MediaFailed
    | MediaWarning
    | MediaEnded
)
