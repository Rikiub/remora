"""Remora exceptions."""


class MediaError(Exception):
    """Base exception."""


class OutputTemplateError(MediaError, KeyError):
    """Output template error."""


class DownloadError(MediaError, ConnectionError):
    """Download error."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class MetadataDownloadError(DownloadError):
    "Metadata download error."


class ProcessingError(MediaError):
    """Postprocessing error."""


class ExtractError(MediaError, ConnectionError):
    """Extraction error."""
