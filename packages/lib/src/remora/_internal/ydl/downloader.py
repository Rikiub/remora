from collections.abc import Callable
from pathlib import Path
from typing import Any

from yt_dlp.utils import DownloadError as YDLDownloadError

from remora._internal.ydl.messages import extract_status_code, sanitize_ydl_error
from remora._internal.ydl.types import YDLExtractInfo, YDLFormatInfo, YDLParams
from remora._internal.ydl.wrapper import YDL
from remora.exceptions import DownloadError, MetadataDownloadError
from remora.types import DEFAULT_RETRIES, StrPath


def download_format(
    filepath: StrPath,
    format_info: YDLFormatInfo,
    callback: Callable[[dict[str, Any]], None] | None = None,
    retries: int = DEFAULT_RETRIES,
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

    return download_from_info(info, params, retries)


def download_from_info(
    info: YDLExtractInfo,
    params: YDLParams,
    retries: int = DEFAULT_RETRIES,
) -> Path:
    config: YDLParams = {"retries": retries, "fragment_retries": retries}

    try:
        ydl = YDL(
            params=config | params,
            auto_init=True,
        )
        result = ydl.process_ie_result(
            info,  # type: ignore
            download=True,
        )
        filepath = result["requested_downloads"][0]["filepath"]  # type: ignore
        return Path(filepath)
    except YDLDownloadError as error:
        raise DownloadError(
            message=sanitize_ydl_error(error),
            status_code=extract_status_code(error),
        )


def download_thumbnail(filepath: StrPath, thumbnail: YDLExtractInfo) -> Path:
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

    try:
        final = ydl._write_thumbnails(  # type: ignore
            label=filepath,
            info_dict=info,
            filename=str(filepath),
        )
    except YDLDownloadError as e:
        raise MetadataDownloadError(str(e))

    if final:
        return Path(final[0][0])
    else:
        raise MetadataDownloadError("Unable to download thumbnail")


def download_subtitles(
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

    try:
        final: list[tuple[str, str]] = ydl._write_subtitles(  # type: ignore
            info_dict=info,
            filename=str(filepath),
        )
    except YDLDownloadError as e:
        raise MetadataDownloadError(str(e))

    if final:
        result = [Path(entry[0]) for entry in final]
        return result
    else:
        raise MetadataDownloadError("Unable to download subtitles")
