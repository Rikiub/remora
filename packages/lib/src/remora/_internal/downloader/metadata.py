from pathlib import Path
from typing import overload

from anyio.to_thread import run_sync

from remora.models.metadata.subtitle import ExternalSubtitle, SubtitleList
from remora.models.metadata.thumbnail import Thumbnail
from remora.types import StrPath


async def download_thumbnail(filepath: StrPath, thumbnail: Thumbnail) -> Path:
    from remora._internal.ydl.downloader import download_thumbnail as ydl

    path = await run_sync(ydl, filepath, thumbnail.to_ydl_dict())
    return path


@overload
async def download_subtitles(filepath, subtitles: ExternalSubtitle) -> Path: ...


@overload
async def download_subtitles(filepath, subtitles: SubtitleList) -> list[Path]: ...


async def download_subtitles(
    filepath: StrPath, subtitles: SubtitleList | ExternalSubtitle
) -> Path | list[Path]:
    from remora._internal.ydl.downloader import download_subtitles as ydl

    paths = await run_sync(ydl, filepath, subtitles.to_ydl_dict())

    if isinstance(subtitles, SubtitleList):
        return paths
    else:
        return paths[0]
