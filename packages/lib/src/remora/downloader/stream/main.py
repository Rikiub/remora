from typing import AsyncIterable

from loguru import logger
from remora.models.progress.stream import StreamEvent

from remora.downloader.stream.base import DEFAULT_RETRIES, BaseStreamDownloader
from remora.downloader.stream.httpx import HttpxStreamDownloader
from remora.exceptions import DownloadError
from remora.models.stream.types import Stream
from remora.types import StrPath
from typing_extensions import override


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
        except* (TypeError, DownloadError) as eg:
            error = eg.exceptions[0]

            is_type_error = isinstance(error, TypeError)
            # TikTok throws 403.
            is_forbidden = isinstance(error, DownloadError) and error.status_code == 403

            if is_type_error or is_forbidden:
                # Logs
                if is_type_error:
                    logger.debug(
                        f'Protocol "{self.stream.protocol}" incompatible with httpx downloader'
                    )
                elif is_forbidden:
                    logger.debug("Webpage blocking access to resource (403 Forbidden)")

                logger.debug("Trying again")

                # Downloader
                from remora.downloader.stream.ydl import YDLFormatDownloader

                downloader = YDLFormatDownloader(
                    self.filepath,
                    self.stream,
                    self.retries,
                )
                async for event in downloader.download():
                    yield event
            else:
                raise
