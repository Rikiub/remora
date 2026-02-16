from collections.abc import AsyncIterable

from loguru import logger
from typing_extensions import override

from remora.downloader.stream.base import DEFAULT_RETRIES, BaseStreamDownloader
from remora.downloader.stream.httpx import HttpxStreamDownloader
from remora.exceptions import DownloadError
from remora.models.event.stream import StreamEvent
from remora.models.stream.types import Stream
from remora.types import StrPath


class StreamDownloader(BaseStreamDownloader):
    def __init__(
        self,
        filepath: StrPath,
        stream: Stream,
        duration: float | None = None,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
    ):
        super().__init__(
            filepath,
            stream,
            retries=retries,
        )
        self.duration = duration
        self.max_workers = max_workers

    @override
    async def download(self) -> AsyncIterable[StreamEvent]:  # type: ignore
        use_fallback = False

        # Main Downloader
        try:
            async with HttpxStreamDownloader(
                self.filepath,
                self.stream,
                retries=self.retries,
                max_workers=self.max_workers,
                duration=self.duration,
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
        from remora.downloader.stream.ydl import YDLStreamDownloader

        downloader = YDLStreamDownloader(
            self.filepath,
            self.stream,
            self.retries,
        )
        async for event in downloader.download():
            yield event
