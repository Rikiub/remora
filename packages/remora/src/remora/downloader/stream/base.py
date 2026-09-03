from anyio import Path
from loguru import logger

from remora.constants import DEFAULT_RETRIES
from remora.downloader._state_streamer import AsyncStateStreamer, T
from remora.models.options.network import NetworkOptions
from remora.models.stream import AudioStream, Stream, VideoStream
from remora.models.types import StrPath

_DEFAULT_BUFFER_SIZE = 100


class BaseStreamDownloader(AsyncStateStreamer[T]):
    SUPPORTED_PROTOCOLS: set[str] | frozenset[str]

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
        network_options: NetworkOptions | None = None,
    ) -> None:
        # General
        self.file_path = Path(output_path)
        self.stream = stream
        self.retries = retries
        self.network_options = network_options or NetworkOptions()
        super().__init__(buffer_size=_DEFAULT_BUFFER_SIZE)

    def _log_stream(self):
        stream_type = "video" if isinstance(self.stream, VideoStream) else "audio"

        logger.bind(status="downloading").debug(
            'Downloading {stream_type} stream "{stream_id}" '
            "(extension:{extension} "
            "| quality:{quality} "
            "| language:{language}) "
            'with "{downloader}"',
            stream_id=self.stream.id,
            stream_type=stream_type,
            quality=self.stream.quality,
            extension=self.stream.extension,
            language=self.stream.audio.language
            if isinstance(self.stream, AudioStream)
            else "unavailable",
            downloader=self.__class__.__name__,
        )
