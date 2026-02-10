from pathlib import Path

from remora.models.content.media import Subtitles
from remora.models.content.metadata import Thumbnail
from remora.models.progress.format import FormatDownloadCallback, FormatState
from remora.types import StrPath


async def download_format(
    self,
    filepath: StrPath,
    on_progress: FormatDownloadCallback | None = None,
) -> Path:
    from remora.ydl.downloader import download_format

    state = FormatState()
    path = await download_format(
        filepath,
        format_info=self.to_ydl_dict(),
        callback=lambda data: state._ydl_progress(
            data,
            on_progress,  # type: ignore
        )
        if on_progress
        else None,
    )
    return path


async def download_thumbnail(filepath: StrPath, thumbnail: Thumbnail) -> Path:
    from remora.ydl.downloader import download_thumbnail as ydl

    return await ydl(filepath, thumbnail.to_ydl_dict())


async def download_subtitles(filepath: StrPath, subtitles: Subtitles) -> list[Path]:
    from remora.ydl.downloader import download_subtitles as ydl

    return await ydl(filepath, subtitles.to_ydl_dict())
