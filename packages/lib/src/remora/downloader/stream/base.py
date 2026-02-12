from abc import ABC

from anyio import Path
from loguru import logger
from remora.models.stream.types import Stream, VideoStream
from remora.types import StrPath

DEFAULT_RETRIES = 3


class BaseStreamDownloader(ABC):
    SUPPORTED_PROTOCOLS: list[str]

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
        type = "video" if isinstance(self.stream, VideoStream) else "audio"
        logger.debug(
            'Downloading {type} stream "{id}" (extension:{extension} | quality:{quality}) with "{class_name}"',
            type=type,
            id=self.stream.id,
            extension=self.stream.extension,
            quality=self.stream.quality,
            class_name=self.__class__.__name__,
        )
