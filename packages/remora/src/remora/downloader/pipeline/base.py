from abc import ABC

from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.downloader.session import DownloadSession

__all__ = ["BaseDownloader"]


class BaseDownloader(AsyncStateStreamer[T], ABC):
    def __init__(self, session: DownloadSession, buffer_size: int | None = None):
        super().__init__(buffer_size=buffer_size)
        self.session = session
