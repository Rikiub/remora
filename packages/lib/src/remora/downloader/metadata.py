from anyio import Path
from anyio.to_thread import run_sync
from remora.models.metadata.subtitles import Subtitles
from remora.models.metadata.thumbnails import Thumbnail
from remora.types import StrPath


async def download_thumbnail(filepath: StrPath, thumbnail: Thumbnail) -> Path:
    from remora.ydl.downloader import download_thumbnail as ydl

    path = await run_sync(ydl, filepath, thumbnail.to_ydl_dict())
    return Path(path)


async def download_subtitles(filepath: StrPath, subtitles: Subtitles) -> list[Path]:
    from remora.ydl.downloader import download_subtitles as ydl

    paths = await run_sync(ydl, filepath, subtitles.to_ydl_dict())
    return [Path(p) for p in paths]
