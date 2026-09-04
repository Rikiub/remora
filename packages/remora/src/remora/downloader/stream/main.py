from loguru import logger
from typing_extensions import override

from remora.constants import DEFAULT_RETRIES, DEFAULT_SEGMENT_WORKERS
from remora.downloader.stream.base import BaseStreamDownloader
from remora.exceptions import DownloaderError
from remora.models.options.network import NetworkOptions
from remora.models.progress import StreamState
from remora.models.stream import Stream
from remora.models.types import StrPath

__all__ = ["StreamDownloader"]


class StreamDownloader(BaseStreamDownloader[StreamState]):
    def __init__(
        self,
        stream: Stream,
        output_path: StrPath,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = DEFAULT_SEGMENT_WORKERS,
        network_options: NetworkOptions | None = None,
    ):
        super().__init__(
            stream=stream,
            output_path=output_path,
            retries=retries,
            network_options=network_options,
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
                from remora.downloader.stream.core.httpx import HttpxStreamDownloader

                async with HttpxStreamDownloader(
                    stream=self.stream,
                    output_path=self.file_path,
                    retries=self.retries,
                    max_workers=self.max_workers,
                    network_options=self.network_options,
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
            from remora.downloader.stream.core.ydl import YDLStreamDownloader

            logger.debug("Retrying with YDL downloader")

            async with YDLStreamDownloader(
                stream=self.stream,
                output_path=self.file_path,
                retries=self.retries,
                network_options=self.network_options,
            ) as progress:
                async for state in progress:
                    await self._emit(state)
