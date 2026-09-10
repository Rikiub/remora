from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Self

from anyio import ContextManagerMixin
from anyio.to_thread import run_sync

from remora._ydl.contextvar import get_ydl_session
from remora._ydl.downloader import YDLDownloader
from remora.models.metadata import Storyboard, Subtitle, Thumbnail
from remora.models.types import StrPath

__all__ = ["MetadataDownloader"]


class MetadataDownloader(ContextManagerMixin):
    def __init__(self): ...

    @asynccontextmanager
    async def __asynccontextmanager__(self) -> AsyncGenerator[Self]:
        with get_ydl_session() as ydl:
            self.downloader = YDLDownloader(ydl)
            yield self

    async def download_resource(
        self,
        item: Subtitle | Thumbnail | Storyboard,
        output_path: StrPath,
    ) -> Path:
        if isinstance(item, Subtitle):
            return await self._download_subtitle(item, output_path)
        elif isinstance(item, Thumbnail):
            return await self._download_thumbnail(item, output_path)
        elif isinstance(item, Storyboard):
            return await self._download_storyboard(item, output_path)

    async def _download_thumbnail(
        self,
        thumbnail: Thumbnail,
        output_path: StrPath,
    ) -> Path:
        path = await run_sync(
            partial(
                self.downloader.download_thumbnail,
                output_path,
                thumbnail._to_ydl_dict(),
            )
        )
        return path

    async def _download_subtitle(
        self,
        subtitle: Subtitle,
        output_path: StrPath,
    ) -> Path:
        paths = await run_sync(
            partial(
                self.downloader.download_subtitles,
                output_path,
                subtitle._to_ydl_dict(),
            )
        )
        return paths[0]

    async def _download_storyboard(
        self,
        storyboard: Storyboard,
        output_path: StrPath,
    ) -> Path:
        path = await run_sync(
            partial(
                self.downloader.download_storyboard,
                output_path,
                storyboard._to_ydl_dict(),
            )
        )
        return path
