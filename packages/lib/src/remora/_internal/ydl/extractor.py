from dataclasses import dataclass
from typing import cast

from yt_dlp.extractor import get_info_extractor
from yt_dlp.utils import DownloadError as YDLDownloadError
from yt_dlp.utils._utils import determine_protocol

from remora._internal.ydl.messages import extract_status_code, sanitize_ydl_error
from remora._internal.ydl.types import YDLExtractInfo
from remora._internal.ydl.wrapper import YDL
from remora.exceptions import ExtractorError
from remora.models.search import SearchService
from remora.types import StrPath


@dataclass(slots=True, frozen=True)
class SearchQuery:
    service: SearchService
    template: str

    def build(self, query: str, limit: int = 20) -> str:
        return self.template.format(limit=limit) + query


SEARCH_QUERIES = {
    SearchQuery("soundcloud", "scsearch{limit}:"),
    SearchQuery("youtube", "ytsearch{limit}:"),
    SearchQuery("ytmusic", "https://music.youtube.com/search?q="),
}


def extract_query(
    query: str,
    service: str | SearchService,
    limit: int = 20,
) -> YDLExtractInfo:
    """Extract info from search service."""

    for item in SEARCH_QUERIES:
        if item.service == service:
            result = extract_info(item.build(query, limit))
            return result

    raise ValueError(f"{service} is invalid. Should be: {SearchService}")


def extract_info(
    query: str,
    cookies_file: StrPath | None = None,
) -> YDLExtractInfo:
    try:
        ydl = YDL(
            params={
                "extract_flat": "in_playlist",
                "skip_download": True,
                "cookiefile": cookies_file,
            },
            auto_init=True,
        )
        info = ydl.extract_info(query, download=False)

        # Normalize extractor fields
        info = _normalize_extractor_field(info)

        entries = info.get("entries") or []
        for index, entry in enumerate(entries):
            entries[index] = _normalize_extractor_field(entry)
        info["entries"] = entries

        # Infer protocol if missing
        if info.get("url"):
            info["protocol"] = determine_protocol(info)
    except YDLDownloadError as error:
        raise ExtractorError(
            message=sanitize_ydl_error(error),
            status_code=extract_status_code(error),
        )

    return cast(YDLExtractInfo, info)


def _normalize_extractor_field(info: dict) -> dict:
    extractor = get_info_extractor(info.get("extractor_key") or info.get("ie_key"))
    info["extractor_key"] = extractor.ie_key()
    info["extractor"] = extractor.IE_NAME
    info.pop("ie_key", None)
    return info
