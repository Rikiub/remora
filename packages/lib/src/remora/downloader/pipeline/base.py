from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.models.options.download import DownloadOptions

__all__ = ["Downloader"]


class Downloader(AsyncStateStreamer[T]):
    def __init__(
        self,
        download_options: DownloadOptions | None = None,
        buffer_size: int | None = None,
    ):
        super().__init__(buffer_size=buffer_size)
        self.download_options = download_options or DownloadOptions()
