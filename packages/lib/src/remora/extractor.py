"""Raw info extractor."""

from typing import overload

from loguru import logger

from remora.cache import load_info, save_info
from remora.models.content.list import LazyPlaylist, Playlist, Search
from remora.models.content.media import LazyMedia, Media
from remora.models.content.types import ExtractAdapter
from remora.types import StrUrl
from remora.ydl.extractor import SEARCH_SERVICE, extract_info, extract_query


class MediaExtractor:
    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache

    @overload
    async def resolve(self, item: LazyMedia) -> Media: ...

    @overload
    async def resolve(self, item: LazyPlaylist) -> Playlist: ...

    async def resolve(self, item: LazyMedia | LazyPlaylist):
        return await self.extract_url(str(item.url))

    async def extract_url(self, url: StrUrl) -> Media | Playlist:
        """Extract media from URL."""

        url = str(url)
        logger.debug("Extract URL: {url}", url=url)

        # Load from cache
        if self.use_cache and (cached_json := load_info(url)):
            model = ExtractAdapter.validate_json(cached_json, by_alias=True)

            if isinstance(model, Media):
                model.is_cache = True

            return model

        # Extract info
        info = await extract_info(url)
        result = ExtractAdapter.validate_python(info, by_alias=True)

        # Save to cache
        if self.use_cache:
            save_info(str(result.url), result.to_ydl_json())

        return result

    async def extract_search(
        self,
        query: str,
        service: SEARCH_SERVICE,
        limit: int = 20,
    ) -> Search:
        """Extract media from search service."""

        logger.debug(
            'Search from "{service}": "{query}".',
            service=service,
            query=query,
        )

        # Load from cache
        if self.use_cache and (cached_json := load_info(query)):
            return Search.from_ydl_json(cached_json)

        # Extract info
        info = await extract_query(query, service, limit)
        result = Search(query=query, service=service, **info)

        # Save to cache
        if self.use_cache:
            save_info(result.query, result.to_ydl_json())

        return result
