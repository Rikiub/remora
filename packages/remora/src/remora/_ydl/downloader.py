from collections.abc import Callable
from pathlib import Path
from typing import Any

from yt_dlp.downloader import get_suitable_downloader
from yt_dlp.downloader.mhtml import MhtmlFD
from yt_dlp.utils import DownloadError as YDLDownloadError

from remora._ydl.messages import extract_status_code, sanitize_ydl_error
from remora._ydl.session import YDL, Session
from remora.constants import DEFAULT_RETRIES
from remora.exceptions import DownloaderError, MetadataDownloaderError
from remora.models.types import AnyDict, StrPath

__all__ = ["Downloader"]


class Downloader:
    def __init__(self, session: Session):
        self.session = session

    def download_format(
        self,
        filepath: StrPath,
        format_info: AnyDict,
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

        return self.download_from_info(info, params, retries=retries)

    def download_from_info(
        self,
        info: AnyDict,
        params: AnyDict,
        retries: int = DEFAULT_RETRIES,
    ) -> Path:
        config = {"retries": retries, "fragment_retries": retries}

        try:
            ydl = YDL(
                params=config | params,
                session=self.session,
                auto_init=True,
            )
            result = ydl.process_ie_result(info, download=True)
            filepath = result["requested_downloads"][0]["filepath"]
            return Path(filepath)
        except YDLDownloadError as error:
            raise DownloaderError(
                message=sanitize_ydl_error(error),
                status_code=extract_status_code(error),
            )

    def download_thumbnail(self, filepath: StrPath, thumbnail: AnyDict) -> Path:
        ydl = YDL(
            {
                "writethumbnail": True,
                "outtmpl": {
                    "thumbnail": "",
                    "pl_thumbnail": "",
                },
            },
            session=self.session,
        )

        info = {"thumbnails": [thumbnail]}

        try:
            final = ydl._write_thumbnails(
                label=filepath,
                info_dict=info,
                filename=str(filepath),
            )
        except YDLDownloadError as e:
            msg = sanitize_ydl_error(e)
            raise MetadataDownloaderError(msg)

        if final:
            return Path(final[0][0])
        else:
            raise MetadataDownloaderError("Unable to download thumbnail")

    def download_subtitles(
        self,
        filepath: StrPath,
        subtitles: AnyDict,
        automatic_captions: AnyDict | None = None,
    ) -> list[Path]:
        automatic_captions = automatic_captions or {}

        ydl = YDL(
            {"writesubtitles": True, "allsubtitles": True},
            session=self.session,
        )
        subs = ydl.process_subtitles(
            str(filepath),
            subtitles,
            automatic_captions,
        )
        info = {"requested_subtitles": subs}

        try:
            final: list[tuple[str, str]] = ydl._write_subtitles(
                info_dict=info,
                filename=str(filepath),
            )
        except YDLDownloadError as e:
            msg = sanitize_ydl_error(e)
            raise MetadataDownloaderError(msg)

        if final:
            result = [Path(entry[0]) for entry in final]
            return result
        else:
            raise MetadataDownloaderError("Unable to download subtitles")

    def download_storyboard(
        self,
        filepath: StrPath,
        storyboard: AnyDict,
    ) -> Path:
        extension = storyboard["ext"]
        filepath = f"{filepath}.{extension}"

        fd_class = get_suitable_downloader(storyboard, {}, protocol="mhtml")
        fd: MhtmlFD = fd_class(YDL(session=self.session), {})
        fd.download(filepath, storyboard)

        return Path(filepath)
