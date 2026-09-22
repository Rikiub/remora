from pathlib import Path

from loguru import logger
from typing_extensions import override

from remora.exceptions import DownloaderError
from remora.models.progress import StreamState
from remora.models.stream import AudioStream, Stream, VideoStream
from remora.models.types import StrPath
from remora.session import Session

from ._base import Downloader

__all__ = ["StreamDownloader"]


class StreamDownloader(Downloader[StreamState]):
    def __init__(
        self,
        stream: Stream,
        output_path: StrPath,
        session: Session | None = None,
    ):
        super().__init__(session=session)
        self.stream = stream
        self.file_path = Path(output_path)

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
                from remora.downloader.stream._core.httpx import HttpxStreamDownloader

                async with HttpxStreamDownloader(
                    stream=self.stream,
                    output_path=self.file_path,
                    client=self.session.httpx_client,
                    retries=self.session.download_options.retries,
                    concurrency=self.session.download_options.concurrency,
                ) as progress:
                    self._log_stream(
                        stream=self.stream,
                        downloader=HttpxStreamDownloader,
                    )

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
            from remora.downloader.stream._core.ydl import YDLStreamDownloader

            logger.debug("Retrying with YDL downloader")

            async with YDLStreamDownloader(
                stream=self.stream,
                output_path=self.file_path,
                ydl_session=self.session.ydl_session,
                retries=self.session.download_options.retries,
            ) as progress:
                self._log_stream(
                    stream=self.stream,
                    downloader=YDLStreamDownloader,
                )

                async for state in progress:
                    await self._emit(state)

    def _log_stream(self, stream: Stream, downloader: type):
        stream_type = "video" if isinstance(stream, VideoStream) else "audio"

        logger.bind(status="downloading").debug(
            'Downloading {stream_type} stream "{stream_id}" '
            "(extension:{extension} "
            "| quality:{quality} "
            "| language:{language}) "
            'with "{downloader}"',
            stream_id=stream.id,
            stream_type=stream_type,
            quality=stream.quality,
            extension=stream.container.extension,
            language=stream.language if isinstance(stream, AudioStream) else "None",
            downloader=downloader,
        )
