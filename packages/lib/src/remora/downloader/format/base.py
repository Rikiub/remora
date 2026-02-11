from abc import ABC

from anyio import Path
from loguru import logger
from remora.models.format.types import Format, VideoFormat
from remora.types import StrPath

DEFAULT_RETRIES = 3


class BaseFormatDownloader(ABC):
    SUPPORTED_PROTOCOLS: list[str]

    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.filepath = Path(filepath)
        self.format = format
        self.retries = retries

    def _log_format(self):
        type = "video" if isinstance(format, VideoFormat) else "audio"
        logger.debug(
            'Downloading {type} format "{format_id}" (extension:{extension} | quality:{quality}) with "{class_name}"',
            type=type,
            format_id=self.format.id,
            extension=self.format.extension,
            quality=self.format.quality,
            class_name=self.__class__.__name__,
        )
