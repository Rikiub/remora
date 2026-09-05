"""Raw info extractor."""

from typing import overload

from anyio.to_thread import run_sync
from loguru import logger

from remora.models.media import (
    ExtractAdapter,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    SearchList,
)
from remora.models.options.network import NetworkOptions
from remora.models.search import SearchService
from remora.models.types import StrUrl

__all__ = ["MediaExtractor"]


class MediaExtractor:
    def __init__(self, network_options: NetworkOptions | None = None):
        self.network_options = network_options or NetworkOptions()

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
            # Logs
            logger.info("Extracting URL: {url}", url=url)

            if cookies := self.network_options.cookies:
                logger.info(
                    "Using cookies list with {cookies_length} items",
                    cookies_length=len(cookies),
                )
            if proxy := self.network_options.proxy:
                logger.info('Using proxy: "{proxy_url}"', proxy=proxy)
            if impersonate := self.network_options.impersonate:
                logger.info(
                    'Using impersonate target: "{impersonate}"', impersonate=impersonate
                )

            # Extract info
            from remora._ydl.extractor import extract_info

            info = await run_sync(extract_info, url, self.network_options)
            result = ExtractAdapter.validate_python(info, by_alias=True)

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
            from remora._ydl.extractor import extract_query

            info = await run_sync(extract_query, query, service, limit)
            result = SearchList.model_validate(
                {"query": query, "service": service, **info},
                by_alias=True,
            )

            logger.success("Search successful")
            return result
