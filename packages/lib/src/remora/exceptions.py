"""Remora exceptions."""


class RemoraError(Exception):
    """Base exception for all Remora errors."""


class OutputTemplateError(RemoraError, ValueError):
    """Raised when an output template path or string formatting is invalid."""


class RequestError(RemoraError, ConnectionError):
    """Base exception for network/connection issues from websites."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ExtractorError(RequestError):
    """Raised when metadata extraction fails."""


class DownloaderError(RequestError):
    """Raised when media content fails to download."""


class MetadataDownloaderError(DownloaderError):
    """Raised when fetching external metadata fails during downloading."""


class ProcessorError(RemoraError):
    """Base exception for post-processing and media transcoding errors."""


class FFmpegNotFoundError(ProcessorError, FileNotFoundError):
    """Raised when the ffmpeg executable is not found."""
