from typing import TypeVar

from remora._internal.downloader.event_streamer import AsyncEventStreamer
from remora._internal.extractor import MediaExtractor
from remora.models.download_options import DownloadOptions

_T = TypeVar("_T")


class Downloader(AsyncEventStreamer[_T]):
    def __init__(
        self,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
        buffer_size: int | None = None,
    ):
        super().__init__(buffer_size=buffer_size)
        self.config = config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()
