from typing import TypeVar

from anyio import Path
from loguru import logger

from remora._internal.downloader.event_streamer import AsyncEventStreamer
from remora.models.stream import Stream, VideoStream
from remora.types import DEFAULT_RETRIES, StrPath

_DEFAULT_BUFFER_SIZE = 100
_T = TypeVar("_T")


class BaseStreamDownloader(AsyncEventStreamer[_T]):
    SUPPORTED_PROTOCOLS: set[str] | frozenset[str]

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.file_path = Path(output_path)
        self.stream = stream
        self.retries = retries
        super().__init__(buffer_size=_DEFAULT_BUFFER_SIZE)

    def _log_stream(self):
        stream_type = "video" if isinstance(self.stream, VideoStream) else "audio"

        logger.bind(status="downloading").debug(
            'Downloading {stream_type} stream "{stream_id}" (extension:{extension} '
            "| quality:{quality}) "
            'with "{downloader}"',
            stream_id=self.stream.id,
            stream_type=stream_type,
            quality=self.stream.quality,
            extension=self.stream.extension,
            downloader=self.__class__.__name__,
        )
