from collections.abc import Sequence
from pathlib import Path
from typing import overload

from remora._internal.downloader.pipeline.batch import BatchDownloader
from remora._internal.downloader.pipeline.media import MediaDownloader
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.extractor import MediaExtractor
from remora.models.download_options import DownloadOptions
from remora.models.media import (
    AnyExtractResult,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    SearchList,
)
from remora.models.metadata import ExternalSubtitle, Thumbnail
from remora.models.search import SearchService
from remora.models.stream import Stream
from remora.types import StrPath, StrUrl


class Remora:
    def __init__(
        self,
        download_options: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.download_options = download_options or DownloadOptions()
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
    ) -> SearchList:
        """Extract media from search service."""
        return await self.extractor.extract_search(query, service, limit)

    @overload
    async def download(
        self, item: StrUrl | LazyMedia | Media | Playlist
    ) -> MediaDownloader: ...

    @overload
    async def download(self, item: LazyPlaylist) -> BatchDownloader: ...

    async def download(
        self, item: StrUrl | LazyMedia | LazyPlaylist
    ) -> MediaDownloader | BatchDownloader:
        extracted = await self.extract(item)

        if isinstance(extracted, LazyPlaylist):
            return BatchDownloader(
                extracted,
                config=self.download_options,
                extractor=self.extractor,
            )
        else:
            return MediaDownloader(
                extracted,
                config=self.download_options,
                extractor=self.extractor,
            )

    def download_batch(self, item: StrUrl | AnyExtractResult) -> BatchDownloader:
        return BatchDownloader(
            item,
            config=self.download_options,
            extractor=self.extractor,
        )

    def download_stream(
        self,
        item: Stream,
        output_path: StrPath,
        retries: int | None = None,
    ) -> StreamDownloader:
        return StreamDownloader(
            output_path,
            stream=item,
            retries=retries or self.download_options.retries,
        )

    @overload
    async def download_resource(
        self, item: Thumbnail | ExternalSubtitle, output_path
    ) -> Path: ...

    @overload
    async def download_resource(
        self, item: Sequence[ExternalSubtitle], output_path
    ) -> list[Path]: ...

    async def download_resource(
        self,
        item: Thumbnail | ExternalSubtitle | Sequence[ExternalSubtitle],
        output_path: StrPath,
    ) -> Path | list[Path]:
        match item:
            case Thumbnail():
                from remora._internal.downloader.metadata import download_thumbnail

                output_path = await download_thumbnail(item, output_path)
                return output_path
            case Sequence() | ExternalSubtitle():
                from remora._internal.downloader.metadata import download_subtitles

                paths = await download_subtitles(item, output_path)
                return paths
