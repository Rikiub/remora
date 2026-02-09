import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from yt_dlp.utils import DownloadError as YDLDownloadError

from remora.exceptions import DownloadError, MetadataDownloadError
from remora.types import StrPath
from remora.ydl.messages import format_except_message
from remora.ydl.types import YDLExtractInfo, YDLFormatInfo, YDLParams
from remora.ydl.wrapper import YDL


async def download_format(
    filepath: StrPath,
    format_info: YDLFormatInfo,
    callback: Callable[[dict[str, Any]], None] | None = None,
) -> Path:
    filepath = Path(filepath)
    params = {}

    if callback:
        params |= {"progress_hooks": [callback]}

    params |= {"outtmpl": f"{filepath}.%(ext)s"}
    info = {
        "extractor": "generic",
        "extractor_key": "Generic",
        "title": filepath.stem,
        "id": filepath.stem,
        "format_id": format_info["format_id"],
        "formats": [format_info],
    }

    return await download_from_info(info, params)


async def download_from_info(info: YDLExtractInfo, params: YDLParams) -> Path:
    retries: YDLParams = {"retries": 0, "fragment_retries": 0}

    try:
        ydl = YDL(
            params=retries | params,
            auto_init=True,
        )
        result = await asyncio.to_thread(
            ydl.process_ie_result,
            info,  # type: ignore
            download=True,
        )
        filepath = result["requested_downloads"][0]["filepath"]  # type: ignore
        return Path(filepath)
    except YDLDownloadError as err:
        msg = format_except_message(err)
        raise DownloadError(msg)


async def download_thumbnail(filepath: StrPath, thumbnail: YDLExtractInfo) -> Path:
    ydl = YDL(
        {
            "writethumbnail": True,
            "outtmpl": {
                "thumbnail": "",
                "pl_thumbnail": "",
            },
        }
    )

    info = {"thumbnails": [thumbnail]}
    final = await asyncio.to_thread(
        ydl._write_thumbnails,  # type: ignore
        label=filepath,
        info_dict=info,
        filename=str(filepath),
    )

    if final:
        return Path(final[0][0])
    else:
        raise MetadataDownloadError("Unable to download thumbnail.")


async def download_subtitles(
    filepath: StrPath,
    subtitles: YDLExtractInfo,
    automatic_captions: YDLExtractInfo = {},
) -> list[Path]:
    ydl = YDL({"writesubtitles": True, "allsubtitles": True})

    subs = ydl.process_subtitles(
        str(filepath),
        subtitles,
        automatic_captions,
    )
    info = {"requested_subtitles": subs}

    final: list[tuple[str, str]] = await asyncio.to_thread(
        ydl._write_subtitles,  # type: ignore
        info_dict=info,
        filename=str(filepath),
    )

    if final:
        result = [Path(entry[0]) for entry in final]
        return result
    else:
        raise MetadataDownloadError("Unable to download subtitles.")
