from collections.abc import AsyncIterable
from typing import overload

from anyio import Path

from remora._internal.extractor import MediaExtractor
from remora.models.content.list import LazyPlaylist, Playlist
from remora.models.content.media import LazyMedia, Media
from remora.models.content.types import AnyExtractResult
from remora.models.download_options import DownloadOptions
from remora.models.event.main import DownloadEvent
from remora.models.event.media import MediaEvent
from remora.models.metadata.thumbnails import Thumbnail
from remora.types import SearchService, StrPath, StrUrl
from remora_cli.ui.extractor import Search


class RemoraAPI:
    def __init__(
        self,
        download_config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.config = download_config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()

    @overload
    async def extract(self, item: StrUrl) -> Media | Playlist: ...

    @overload
    async def extract(self, item: LazyMedia) -> Media: ...

    @overload
    async def extract(self, item: LazyPlaylist) -> Playlist: ...

    async def extract(
        self, item: StrUrl | LazyMedia | LazyPlaylist
    ) -> Media | Playlist:
        """Extract media from URL or update item."""
        return await self.extractor.extract(item)

    async def extract_search(
        self,
        query: str,
        service: SearchService,
        limit: int = 20,
    ) -> Search:
        """Extract media from search service."""
        return await self.extractor.extract_search(query, service, limit)

    @overload
    def download(self, item: StrUrl | LazyMedia) -> AsyncIterable[MediaEvent]: ...

    @overload
    def download(self, item: Media | Playlist) -> AsyncIterable[MediaEvent]: ...

    @overload
    def download(self, item: LazyPlaylist) -> AsyncIterable[DownloadEvent]: ...

    async def download(
        self, item: StrUrl | LazyMedia | LazyPlaylist
    ) -> AsyncIterable[MediaEvent | DownloadEvent]:
        extracted = await self.extract(item)

        if isinstance(extracted, LazyPlaylist):
            async for event in self.download_batch(extracted):
                if event.type == "media":
                    yield event
        else:
            from remora._internal.downloader.pipeline import DownloadPipeline

            async for event in DownloadPipeline(
                extracted,
                format_config=self.config,
                extractor=self.extractor,
            ).download():
                yield event

    async def download_batch(
        self,
        item: StrUrl | AnyExtractResult,
    ) -> AsyncIterable[DownloadEvent]:
        if isinstance(item, StrUrl):
            extracted = await self.extract(item)
        else:
            extracted = item

        from remora._internal.downloader.batch import DownloadBatch

        async for event in DownloadBatch(
            extracted,
            format_config=self.config,
            extractor=self.extractor,
        ).download():
            yield event

    async def download_resource(self, item: Thumbnail, path: StrPath) -> Path:
        match item:
            case Thumbnail():
                from remora._internal.downloader.metadata import download_thumbnail

                thumbnail = await download_thumbnail(path, item)
                return thumbnail
