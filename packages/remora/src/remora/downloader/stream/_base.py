from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.session import Session


class Downloader(AsyncStateStreamer[T]):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__(buffer_size=100)
        self.session = session or Session.create()
