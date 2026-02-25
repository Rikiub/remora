from enum import StrEnum


class EventType(StrEnum):
    MEDIA = "media"
    PLAYLIST = "playlist"


class EventStatus(StrEnum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WARNING = "warning"
    FAILED = "failed"
    CANCELLED = "cancelled"

    EXTRACTING = "extracting"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"


class CompletedResult(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    DUPLICATE = "duplicate"
