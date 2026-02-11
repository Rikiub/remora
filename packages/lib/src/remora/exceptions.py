"""Remora exceptions."""


class MediaError(Exception):
    """Base exception."""


class OutputTemplateError(MediaError, KeyError):
    """Output template error."""


class CancelledError(MediaError): ...


class MediaConnectionError(MediaError, ConnectionError):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ExtractError(MediaConnectionError):
    """Extraction error."""


class DownloadError(MediaConnectionError):
    """Download error."""


class MetadataDownloadError(DownloadError):
    "Metadata download error."


class ProcessingError(MediaError):
    """Postprocessing error."""
