from functools import partial
from pathlib import Path

from anyio import AsyncContextManagerMixin
from anyio.to_thread import run_sync
from typing_extensions import override

from remora._ydl.downloader import YDLDownloader
from remora._ydl.wrapper import YDLNetworkContext
from remora.models.metadata import Storyboard, Subtitle, Thumbnail
from remora.models.types import StrPath

__all__ = ["MetadataDownloader"]


class MetadataDownloader(AsyncContextManagerMixin):
    def __init__(self, ydl_context: YDLNetworkContext | None = None):
        self._ydl_downloader = YDLDownloader(ydl_context)

    @override
    def __asynccontextmanager__(self):
        pass

    async def download_resource(
        self,
        item: Subtitle | Thumbnail | Storyboard,
        output_path: StrPath,
    ) -> Path:
        if isinstance(item, Subtitle):
            return await self.download_subtitle(item, output_path)
        elif isinstance(item, Thumbnail):
            return await self.download_thumbnail(item, output_path)
        elif isinstance(item, Storyboard):
            return await self.download_storyboard(item, output_path)

    async def download_thumbnail(
        self,
        thumbnail: Thumbnail,
        output_path: StrPath,
    ) -> Path:
        path = await run_sync(
            partial(
                self._ydl_downloader.download_thumbnail,
                output_path,
                thumbnail._to_ydl_dict(),
            )
        )
        return path

    async def download_subtitle(
        self,
        subtitle: Subtitle,
        output_path: StrPath,
    ) -> Path:
        paths = await run_sync(
            partial(
                self._ydl_downloader.download_subtitles,
                output_path,
                subtitle._to_ydl_dict(),
            )
        )
        return paths[0]

    async def download_storyboard(
        self,
        storyboard: Storyboard,
        output_path: StrPath,
    ) -> Path:
        path = await run_sync(
            partial(
                self._ydl_downloader.download_storyboard,
                output_path,
                storyboard._to_ydl_dict(),
            )
        )
        return path
