"""Raw info extractor."""

from functools import partial
from typing import overload

from anyio.to_thread import run_sync
from loguru import logger
from pydantic import AnyUrl

from remora._ydl import Extractor
from remora.models.media import (
    ExtractAdapter,
    LazyMedia,
    LazyPlaylist,
    Media,
    Playlist,
    Search,
)
from remora.models.search import SearchService
from remora.models.types import StrUrl
from remora.session import Session

__all__ = ["MediaExtractor"]


class MediaExtractor:
    def __init__(self, session: Session):
        self._session = session
        self._ydl_extractor = Extractor(session.ydl_session)

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

            if cookies := self._session.network_options.cookies:
                logger.info(
                    "Using cookies list with {cookies_length} items",
                    cookies_length=len(cookies),
                )

                if (url_host := AnyUrl(url).host) and (
                    cookies.get_expired_cookies(url_host)
                ):
                    logger.warning(
                        f"The given cookies for the domain '{url_host}' are expired. "
                        "It could do unexpected behaviour. "
                        "Please update your cookies the next time."
                    )
            if proxy := self._session.network_options.proxy:
                logger.info('Using proxy: "{proxy_url}"', proxy=proxy)
            if impersonate := self._session.network_options.impersonate:
                logger.info(
                    'Using impersonate target: "{impersonate}"', impersonate=impersonate
                )

            # Extract info
            info = await run_sync(partial(self._ydl_extractor.extract_info, query=url))
            result = ExtractAdapter.validate_python(info, by_alias=True)

            logger.success("Extraction successful")
            return result

    async def extract_search(
        self,
        query: str,
        service: SearchService,
        limit: int = 20,
    ) -> Search:
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
            info = await run_sync(
                partial(
                    self._ydl_extractor.extract_query,
                    query=query,
                    service=service,
                    limit=limit,
                )
            )
            result = Search.model_validate(
                {"query": query, "service": service, **info},
                by_alias=True,
            )

            logger.success("Search successful")
            return result
