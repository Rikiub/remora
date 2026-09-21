from abc import ABC

from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.session import Session

__all__ = ["BaseDownloader"]


class BaseDownloader(AsyncStateStreamer[T], ABC):
    def __init__(self, session: Session, buffer_size: int | None = None):
        super().__init__(buffer_size=buffer_size)
        self.session = session
