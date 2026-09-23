from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Self, overload

from anyio import AsyncContextManagerMixin
from typing_extensions import override

from remora.downloader import (
    MediaDownloader,
    MetadataDownloader,
    PlaylistDownloader,
    StreamDownloader,
)
from remora.extractor import MediaExtractor
from remora.models.media import (
    AnyExtractResult,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    Search,
)
from remora.models.metadata import Storyboard, Subtitle, Thumbnail
from remora.models.options import DownloadOptions, NetworkOptions
from remora.models.search import SearchService
from remora.models.stream import Stream
from remora.models.types import StrPath, StrUrl
from remora.session import Session

__all__ = ["Remora"]


class Remora(AsyncContextManagerMixin):
    def __init__(
        self,
        download_options: DownloadOptions | None = None,
        network_options: NetworkOptions | None = None,
    ):
        self.download_options = download_options or DownloadOptions()
        self.network_options = network_options or NetworkOptions()

        self._session = Session.create(
            download_options=self.download_options,
            network_options=self.network_options,
            extract_limit=self.download_options.concurrency,
            download_limit=self.download_options.concurrency,
        )
        self._extractor = MediaExtractor(self._session)
        self._metadata = MetadataDownloader(self._session)

    @override
    @asynccontextmanager
    async def __asynccontextmanager__(self) -> AsyncGenerator[Self, None]:
        async with self._session:
            yield self

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
    ) -> Search:
        """Extract media from search service."""
        return await self._extractor.extract_search(query, service, limit)

    def download_playlist(self, item: StrUrl | AnyExtractResult) -> PlaylistDownloader:
        return PlaylistDownloader(item, self._session)

    def download_media(self, media: Media) -> MediaDownloader:
        return MediaDownloader(media, self._session)

    def download_stream(self, stream: Stream, output_path: StrPath) -> StreamDownloader:
        return StreamDownloader(
            stream=stream,
            output_path=output_path,
            session=self._session,
        )

    async def download_resource(
        self,
        item: Subtitle | Thumbnail | Storyboard,
        output_path: StrPath,
    ) -> Path:
        return await self._metadata.download_resource(item, output_path)
