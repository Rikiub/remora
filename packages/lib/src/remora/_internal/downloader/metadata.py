from pathlib import Path
from typing import overload

from anyio.to_thread import run_sync

from remora.models.metadata import ExternalSubtitle, SubtitleList, Thumbnail
from remora.types import StrPath


async def download_thumbnail(thumbnail: Thumbnail, output_path: StrPath) -> Path:
    from remora._internal.ydl.downloader import download_thumbnail as ydl

    path = await run_sync(ydl, output_path, thumbnail._to_ydl_dict())
    return path


@overload
async def download_subtitles(subtitles: ExternalSubtitle, output_path) -> Path: ...


@overload
async def download_subtitles(
    subtitles: SubtitleList | list[ExternalSubtitle], output_path
) -> list[Path]: ...


async def download_subtitles(
    subtitles: SubtitleList | ExternalSubtitle | list[ExternalSubtitle],
    output_path: StrPath,
) -> Path | list[Path]:
    from remora._internal.ydl.downloader import download_subtitles as ydl

    if isinstance(subtitles, list):
        info = SubtitleList(subtitles)._to_ydl_dict()
    else:
        info = subtitles._to_ydl_dict()

    paths = await run_sync(ydl, output_path, info)

    if isinstance(subtitles, SubtitleList):
        return paths
    else:
        return paths[0]
