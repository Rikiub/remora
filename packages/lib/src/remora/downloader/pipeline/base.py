from remora.downloader._state_streamer import _T, AsyncStateStreamer
from remora.extractor import MediaExtractor
from remora.models.download_options import DownloadOptions

__all__ = ["Downloader"]


class Downloader(AsyncStateStreamer[_T]):
    def __init__(
        self,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
        buffer_size: int | None = None,
    ):
        super().__init__(buffer_size=buffer_size)
        self.config = config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()
