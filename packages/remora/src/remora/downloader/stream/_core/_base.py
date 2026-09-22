from anyio import Path

from remora.constants import DEFAULT_RETRIES
from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.models.stream import Stream
from remora.models.types import StrPath


class Downloader(AsyncStateStreamer[T]):
    SUPPORTED_PROTOCOLS: set[str] | frozenset[str]

    def __init__(
        self,
        stream: Stream,
        output_path: StrPath,
        retries: int | None = None,
    ) -> None:
        super().__init__(buffer_size=100)
        self.stream = stream
        self.file_path = Path(output_path)
        self.retries = retries or DEFAULT_RETRIES
