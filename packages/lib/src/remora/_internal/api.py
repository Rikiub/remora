from collections.abc import AsyncIterable
from pathlib import Path
from typing import overload

from remora._internal.extractor import MediaExtractor
from remora._internal.types.search import SearchServiceLike
from remora.models.download_options import DownloadOptions
from remora.models.event.media import MediaEvent
from remora.models.event.playlist import BatchEvent
from remora.models.event.stream import StreamEvent
from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, Playlist
from remora.models.media.types import AnyExtractResult
from remora.models.metadata.subtitle import ExternalSubtitle, SubtitleList
from remora.models.metadata.thumbnail import Thumbnail
from remora.models.stream.item import Stream
from remora.types import StrPath, StrUrl
from remora_cli.ui.extractor import SearchList


class Remora:
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
        service: SearchServiceLike,
        limit: int = 20,
    ) -> SearchList:
        """Extract media from search service."""
        return await self.extractor.extract_search(query, service, limit)

    @overload
    def download(self, item: StrUrl | LazyMedia) -> AsyncIterable[MediaEvent]: ...

    @overload
    def download(self, item: Media | Playlist) -> AsyncIterable[MediaEvent]: ...

    @overload
    def download(self, item: LazyPlaylist) -> AsyncIterable[BatchEvent]: ...

    async def download(
        self, item: StrUrl | LazyMedia | LazyPlaylist
    ) -> AsyncIterable[MediaEvent | BatchEvent]:
        extracted = await self.extract(item)

        if isinstance(extracted, LazyPlaylist):
            async for event in self.download_batch(extracted):
                if event.type == "media":
                    yield event
        else:
            from remora._internal.downloader.pipeline import DownloadPipeline

            async for event in DownloadPipeline(
                extracted,
                config=self.config,
                extractor=self.extractor,
            ).download():
                yield event

    async def download_batch(
        self, item: StrUrl | AnyExtractResult
    ) -> AsyncIterable[BatchEvent]:
        if isinstance(item, StrUrl):
            extracted = await self.extract(item)
        else:
            extracted = item

        from remora._internal.downloader.batch import DownloadBatch

        async for event in DownloadBatch(
            extracted,
            config=self.config,
            extractor=self.extractor,
        ).download():
            yield event

    async def download_stream(
        self,
        item: Stream,
        output_path: StrPath,
        retries: int | None = None,
    ) -> AsyncIterable[StreamEvent]:
        from remora._internal.downloader.stream.main import StreamDownloader

        downloader = StreamDownloader(
            output_path,
            item,
            retries=retries or self.config.retries,
        )
        async for event in downloader.download():
            yield event

    @overload
    async def download_resource(self, item: Thumbnail, output_path) -> Path: ...

    @overload
    async def download_resource(self, item: ExternalSubtitle, output_path) -> Path: ...

    @overload
    async def download_resource(
        self, item: SubtitleList | list[ExternalSubtitle], output_path
    ) -> list[Path]: ...

    async def download_resource(
        self,
        item: Thumbnail | ExternalSubtitle | SubtitleList | list[ExternalSubtitle],
        output_path: StrPath,
    ) -> Path | list[Path]:
        match item:
            case Thumbnail():
                from remora._internal.downloader.metadata import download_thumbnail

                output_path = await download_thumbnail(item, output_path)
                return output_path
            case list() | SubtitleList() | ExternalSubtitle():
                from remora._internal.downloader.metadata import download_subtitles

                paths = await download_subtitles(item, output_path)
                return paths
