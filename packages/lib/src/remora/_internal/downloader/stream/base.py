from abc import ABC

from anyio import Path
from loguru import logger

from remora.models.stream.types import Stream, VideoStream
from remora.types import StrPath

DEFAULT_RETRIES = 3


class BaseStreamDownloader(ABC):
    SUPPORTED_PROTOCOLS: set[str] | frozenset[str]

    def __init__(
        self,
        filepath: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.filepath = Path(filepath)
        self.stream = stream
        self.retries = retries

    def _log_stream(self):
        stream_type = "video" if isinstance(self.stream, VideoStream) else "audio"

        data = {
            "status": "downloading",
            "stream_id": self.stream.id,
            "stream_type": stream_type,
            "quality": self.stream.quality,
            "extension": self.stream.extension,
            "downloader": self.__class__.__name__,
        }

        logger.bind(**data).debug(
            'Downloading {stream_type} stream "{stream_id}" (extension:{extension} | quality:{quality}) with "{downloader}"',
            **data,
        )
