from collections.abc import AsyncIterable

from loguru import logger
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora._internal.downloader.stream.httpx import HttpxStreamDownloader
from remora.exceptions import DownloadError
from remora.models.event.stream import StreamEvent
from remora.models.stream.item import Stream
from remora.types import DEFAULT_RETRIES, StrPath


class StreamDownloader(BaseStreamDownloader):
    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
    ):
        super().__init__(
            output_path,
            stream,
            retries=retries,
        )
        self.max_workers = max_workers

    @override
    async def download(self) -> AsyncIterable[StreamEvent]:  # type: ignore
        use_fallback = False

        with logger.contextualize(
            stream_url=str(self.stream.url),
            stream_type=self.stream.type,
            stream_protocol=self.stream.protocol,
        ):
            # Main Downloader
            try:
                async with HttpxStreamDownloader(
                    self.file_path,
                    self.stream,
                    retries=self.retries,
                    max_workers=self.max_workers,
                ) as client:
                    async for event in client.download():
                        yield event
                    return
            except* (TypeError, DownloadError) as eg:
                error = eg.exceptions[0]

                if isinstance(error, TypeError):
                    logger.debug(
                        'Protocol "{protocol}" incompatible with httpx downloader',
                        protocol=self.stream.protocol,
                    )
                    use_fallback = True
                elif isinstance(error, DownloadError) and error.status_code == 403:
                    logger.debug("Webpage blocking access to resource (403 Forbidden)")
                    use_fallback = True

                if not use_fallback:
                    raise error

            # Fallback downloader
            from remora._internal.downloader.stream.ydl import YDLStreamDownloader

            logger.debug("Retrying with other downloader")

            downloader = YDLStreamDownloader(
                self.file_path,
                self.stream,
                self.retries,
            )
            async for event in downloader.download():
                yield event
