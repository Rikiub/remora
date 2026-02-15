"""Raw info extractor."""

from typing import Callable, TypeVar, overload

from anyio.to_thread import run_sync
from loguru import logger

from pydantic import ValidationError
from remora.cache import load_info, remove_info, save_info
from remora.models.base import YDLSerializable
from remora.models.content.list import LazyPlaylist, Playlist, Search
from remora.models.content.media import LazyMedia, Media
from remora.models.content.types import ExtractAdapter
from remora.types import SEARCH_SERVICE, StrUrl

T = TypeVar("T", bound=YDLSerializable)


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

        from remora.ydl.extractor import extract_info

        url = str(url)
        logger.debug("Extract URL: {url}", url=url)

        # Load from cache
        if model := await self._extract_from_cache(url, ExtractAdapter.validate_json):
            if isinstance(model, Media):
                model.is_cache = True
            return model

        # Extract info
        info = await run_sync(extract_info, url)
        result = ExtractAdapter.validate_python(info)

        # Save to cache
        if self.use_cache:
            await save_info(str(result.url), result.model_dump_json())

        return result

    async def extract_search(
        self,
        query: str,
        service: SEARCH_SERVICE,
        limit: int = 20,
    ) -> Search:
        """Extract media from search service."""

        from remora.ydl.extractor import extract_query

        logger.debug(
            'Search from "{service}": "{query}"',
            service=service,
            query=query,
        )

        # Load from cache
        if model := await self._extract_from_cache(query, Search.model_validate):
            return model

        # Extract info
        info = await run_sync(extract_query, query, service, limit)
        result = Search(query=query, service=service, **info)

        # Save to cache
        if self.use_cache:
            await save_info(result.query, result.model_dump_json())

        return result

    async def _extract_from_cache(
        self,
        query: str,
        validator: Callable[[str], T],
    ) -> T | None:
        try:
            if self.use_cache and (cached_data := await load_info(query)):
                return validator(cached_data)
        except ValidationError as e:
            logger.exception(e)
            logger.debug("Cache is corrupted, deleting.")
            await remove_info(query)

        return None
