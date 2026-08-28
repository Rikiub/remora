from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.models.download_options import DownloadOptions

__all__ = ["Downloader"]


class Downloader(AsyncStateStreamer[T]):
    def __init__(
        self,
        config: DownloadOptions | None = None,
        buffer_size: int | None = None,
    ):
        super().__init__(buffer_size=buffer_size)
        self.config = config or DownloadOptions()
