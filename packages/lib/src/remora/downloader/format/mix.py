from typing import AsyncIterable

from loguru import logger
from remora.models.progress.format import FormatState

from remora.downloader.format.base import DEFAULT_RETRIES, BaseFormatDownloader
from remora.downloader.format.httpx import HttpxFormatDownloader
from remora.exceptions import DownloadError
from remora.models.format.types import Format
from remora.types import StrPath
from typing_extensions import override


class FormatDownloader(BaseFormatDownloader):
    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        duration: float | None = None,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
    ):
        super().__init__(
            filepath,
            format,
            retries=retries,
        )
        self.duration = duration
        self.max_workers = max_workers

    @override
    async def download(self) -> AsyncIterable[FormatState]:  # type: ignore
        try:
            async with HttpxFormatDownloader(
                self.filepath,
                self.format,
                retries=self.retries,
                max_workers=self.max_workers,
                duration=self.duration,
            ) as client:
                async for state in client.download():
                    yield state
        except* (TypeError, DownloadError) as eg:
            error = eg.exceptions[0]

            is_type_error = isinstance(error, TypeError)
            # TikTok throws 403.
            is_forbidden = isinstance(error, DownloadError) and error.status_code == 403

            if is_type_error or is_forbidden:
                # Logs
                if is_type_error:
                    logger.debug(
                        f'Protocol "{self.format.protocol}" incompatible with httpx downloader.'
                    )
                elif is_forbidden:
                    logger.debug("Webpage blocking access to resource (403 Forbidden).")

                logger.debug("Trying again.")

                # Downloader
                from remora.downloader.format.ydl import YDLFormatDownloader

                downloader = YDLFormatDownloader(
                    self.filepath,
                    self.format,
                    self.retries,
                )
                async for state in downloader.download():
                    yield state
            else:
                raise
