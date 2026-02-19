"""Raw info extractor."""

from collections.abc import Callable
from typing import TypeVar, overload

from anyio.to_thread import run_sync
from loguru import logger
from pydantic import ValidationError

from remora._internal.cache import load_info, remove_info, save_info
from remora.models._base import YDLSerializable
from remora.models.media._base import BaseExtract
from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, Playlist, SearchList
from remora.models.media.types import ExtractAdapter
from remora.types import SearchService, StrUrl

T = TypeVar("T", bound=YDLSerializable)


class MediaExtractor:
    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache

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

        url = str(item) if isinstance(item, StrUrl) else str(item.url)

        with logger.contextualize(status="extracting", url=url):
            logger.info("Extracting URL: {url}", url=url)

            # Load from cache
            if model := await self._extract_from_cache(
                url, ExtractAdapter.validate_json
            ):
                if isinstance(model, BaseExtract):
                    model.is_cache = True
                return model

            # Extract info
            from remora._internal.ydl.extractor import extract_info

            info = await run_sync(extract_info, url)
            result = ExtractAdapter.validate_python(info, by_alias=True)

            logger.success("Extraction successful")

            # Save to cache
            await self._save_to_cache(url, result)

            return result

    async def extract_search(
        self,
        query: str,
        service: SearchService,
        limit: int = 20,
    ) -> SearchList:
        """Extract media from search service."""

        with logger.contextualize(status="extracting", service=service, query=query):
            logger.info(
                'Searching from "{service}": "{query}"',
                service=service,
                query=query,
            )

            # Load from cache
            if model := await self._extract_from_cache(
                query, SearchList.model_validate_json
            ):
                return model

            # Extract info
            from remora._internal.ydl.extractor import extract_query

            info = await run_sync(extract_query, query, service, limit)
            result = SearchList.model_validate(
                {"query": query, "service": service, **info},
                by_alias=True,
            )

            logger.success("Search successful")

            # Save to cache
            await self._save_to_cache(result.query, result)

            return result

    async def _extract_from_cache(
        self,
        string: str,
        validator: Callable[[str], T],
    ) -> T | None:
        try:
            if self.use_cache and (cached_data := await load_info(string)):
                model = validator(cached_data)
                logger.success("Data extracted from cache")
                return model
        except ValidationError:
            logger.opt(exception=True).debug("Cache is corrupted, trying again")
            await remove_info(string)

        return None

    async def _save_to_cache(self, query: str, model: BaseExtract):
        if self.use_cache:
            logger.debug("Data saved to cache")
            await save_info(query, model.model_dump_json())
