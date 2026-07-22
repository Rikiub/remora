"""Remora exceptions."""


class RemoraError(Exception):
    """Base remora exception."""


class OutputTemplateError(RemoraError, ValueError):
    """Output template error."""


class MediaConnectionError(RemoraError, ConnectionError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ExtractError(MediaConnectionError):
    """Extraction error."""


class DownloadError(MediaConnectionError):
    """Download error."""


class MetadataDownloadError(DownloadError):
    "Metadata download error."


class ProcessingError(RemoraError):
    """Processing error."""


class FFmpegNotFoundError(ProcessingError, FileNotFoundError): ...
