from pathlib import Path

from anyio.to_thread import run_sync

from remora.models.metadata import Subtitle, Thumbnail
from remora.models.types import StrPath

__all__ = [
    "download_resource",
    "download_subtitle",
    "download_thumbnail",
]


async def download_thumbnail(thumbnail: Thumbnail, output_path: StrPath) -> Path:
    from remora._ydl.downloader import download_thumbnail as ydl

    path = await run_sync(ydl, output_path, thumbnail._to_ydl_dict())
    return path


async def download_subtitle(subtitle: Subtitle, output_path: StrPath) -> Path:
    from remora._ydl.downloader import download_subtitles as ydl

    info = subtitle._to_ydl_dict()
    paths = await run_sync(ydl, output_path, info)

    return paths[0]


async def download_resource(item: Thumbnail | Subtitle, output_path: StrPath) -> Path:
    if isinstance(item, Subtitle):
        paths = await download_subtitle(item, output_path)
        return paths
    elif isinstance(item, Thumbnail):
        output_path = await download_thumbnail(item, output_path)
        return output_path
