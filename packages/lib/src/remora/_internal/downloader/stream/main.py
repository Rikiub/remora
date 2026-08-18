from loguru import logger
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora._internal.downloader.stream.httpx import HttpxStreamDownloader
from remora.exceptions import DownloaderError
from remora.models.progress import StreamState
from remora.models.stream import Stream
from remora.types import DEFAULT_RETRIES, StrPath


class StreamDownloader(BaseStreamDownloader[StreamState]):
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
    async def _run_pipeline(self) -> None:
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
                ) as progress:
                    async for state in progress:
                        await self._emit(state)
                    return
            except (TypeError, DownloaderError) as error:
                if isinstance(error, TypeError):
                    logger.debug(
                        'Protocol "{protocol}" incompatible with httpx downloader',
                        protocol=self.stream.protocol,
                    )
                    use_fallback = True
                elif isinstance(error, DownloaderError) and error.status_code == 403:
                    logger.debug("Webpage blocking access to resource (403 Forbidden)")
                    use_fallback = True

                if not use_fallback:
                    raise

            # Fallback downloader
            from remora._internal.downloader.stream.ydl import YDLStreamDownloader

            logger.debug("Retrying with other downloader")

            async with YDLStreamDownloader(
                self.file_path,
                self.stream,
                self.retries,
            ) as progress:
                async for state in progress:
                    await self._emit(state)
