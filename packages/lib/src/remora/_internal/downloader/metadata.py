from collections.abc import Sequence
from pathlib import Path
from typing import overload

from anyio.to_thread import run_sync

from remora.models.metadata import Subtitle, SubtitleList, Thumbnail
from remora.models.types import StrPath


async def download_thumbnail(thumbnail: Thumbnail, output_path: StrPath) -> Path:
    from remora._internal.ydl.downloader import download_thumbnail as ydl

    path = await run_sync(ydl, output_path, thumbnail._to_ydl_dict())
    return path


@overload
async def download_subtitles(subtitles: Subtitle, output_path) -> Path: ...


@overload
async def download_subtitles(
    subtitles: Sequence[Subtitle], output_path
) -> list[Path]: ...


async def download_subtitles(
    subtitles: Sequence[Subtitle] | Subtitle,
    output_path: StrPath,
) -> Path | list[Path]:
    from remora._internal.ydl.downloader import download_subtitles as ydl

    data = SubtitleList(subtitles)
    info = data._to_ydl_dict()
    paths = await run_sync(ydl, output_path, info)

    if isinstance(subtitles, Sequence):
        return paths
    else:
        return paths[0]


@overload
async def download_resource(
    item: Thumbnail | Subtitle,
    output_path,
) -> Path: ...


@overload
async def download_resource(
    item: Sequence[Subtitle],
    output_path,
) -> list[Path]: ...


async def download_resource(
    item: Thumbnail | Subtitle | Sequence[Subtitle],
    output_path: StrPath,
) -> Path | list[Path]:
    if isinstance(item, (Subtitle, Sequence)):
        paths = await download_subtitles(item, output_path)
        return paths
    elif isinstance(item, Thumbnail):
        output_path = await download_thumbnail(item, output_path)
        return output_path
