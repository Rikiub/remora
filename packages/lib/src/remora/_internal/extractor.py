"""Raw info extractor."""

from typing import overload

from anyio.to_thread import run_sync
from loguru import logger

from remora.models.media import (
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    SearchList,
    _ExtractAdapter,
)
from remora.models.search import SearchService
from remora.models.types import StrPath, StrUrl


class MediaExtractor:
    def __init__(
        self,
        cookies_file: StrPath | None = None,
        proxy_url: StrUrl | None = None,
    ):
        self.cookies_file = cookies_file
        self.proxy_url = proxy_url

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

        url = str(item if isinstance(item, StrUrl) else item.url)

        with logger.contextualize(status="extracting", url=url):
            logger.info("Extracting URL: {url}", url=url)

            # Extract info
            from remora._internal.ydl.extractor import extract_info

            if self.cookies_file:
                logger.info(
                    'Using cookies file "{cookies_file}"',
                    cookies_file=self.cookies_file,
                )
            if self.proxy_url:
                logger.info('Using proxy: "{proxy_url}"', proxy_url=self.proxy_url)

            info = await run_sync(extract_info, url, self.cookies_file, self.proxy_url)
            result = _ExtractAdapter.validate_python(info, by_alias=True)

            logger.success("Extraction successful")
            return result

    async def extract_search(
        self,
        query: str,
        service: SearchService,
        limit: int = 20,
    ) -> SearchList:
        """Extract media from search service."""

        with logger.contextualize(
            status="extracting",
            service=str(service),
            query=query,
        ):
            logger.info(
                'Searching from "{service}": "{query}"',
                service=service,
                query=query,
            )

            # Extract info
            from remora._internal.ydl.extractor import extract_query

            info = await run_sync(extract_query, query, service, limit)
            result = SearchList.model_validate(
                {"query": query, "service": service, **info},
                by_alias=True,
            )

            logger.success("Search successful")
            return result
