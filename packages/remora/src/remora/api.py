from pathlib import Path
from typing import overload

from remora.constants import DEFAULT_SEGMENT_WORKERS
from remora.downloader.pipeline import BatchDownloader, MediaDownloader
from remora.downloader.stream import StreamDownloader
from remora.extractor import MediaExtractor
from remora.models.media import (
    AnyExtractResult,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    SearchList,
)
from remora.models.metadata import Storyboard, Subtitle, Thumbnail
from remora.models.options.download import DownloadOptions
from remora.models.options.network import NetworkOptions
from remora.models.search import SearchService
from remora.models.stream import Stream
from remora.models.types import StrPath, StrUrl

__all__ = ["Remora"]


class Remora:
    def __init__(
        self,
        download_options: DownloadOptions | None = None,
        network_options: NetworkOptions | None = None,
    ):
        self.download_options = download_options or DownloadOptions()
        self.network_options = network_options or NetworkOptions()
        self._extractor = MediaExtractor(self.network_options)

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
        return await self._extractor.extract(item)

    async def extract_search(
        self,
        query: str,
        service: SearchService,
        limit: int = 20,
    ) -> SearchList:
        """Extract media from search service."""
        return await self._extractor.extract_search(query, service, limit)

    def download_media(self, media: Media) -> MediaDownloader:
        return MediaDownloader(
            media,
            download_options=self.download_options,
            network_options=self.network_options,
        )

    def download_batch(self, item: StrUrl | AnyExtractResult) -> BatchDownloader:
        return BatchDownloader(
            item,
            download_options=self.download_options,
            network_options=self.network_options,
        )

    def download_stream(
        self,
        stream: Stream,
        output_path: StrPath,
        retries: int | None = None,
        max_workers: int | None = None,
    ) -> StreamDownloader:
        return StreamDownloader(
            stream=stream,
            output_path=output_path,
            retries=retries or self.download_options.retries,
            max_workers=max_workers or DEFAULT_SEGMENT_WORKERS,
            network_options=self.network_options,
        )

    async def download_resource(
        self,
        item: Thumbnail | Subtitle | Storyboard,
        output_path: StrPath,
    ) -> Path:
        from remora.downloader.metadata import download_resource

        return await download_resource(item, output_path)
