from pathlib import Path

from remora.models.content.media import Subtitles
from remora.models.content.metadata import Thumbnail
from remora.types import StrPath


async def download_thumbnail(filepath: StrPath, thumbnail: Thumbnail) -> Path:
    from remora.ydl.downloader import download_thumbnail as ydl

    return await ydl(filepath, thumbnail.to_ydl_dict())


async def download_subtitles(filepath: StrPath, subtitles: Subtitles) -> list[Path]:
    from remora.ydl.downloader import download_subtitles as ydl

    return await ydl(filepath, subtitles.to_ydl_dict())
