from dataclasses import dataclass
from typing import cast

from yt_dlp.utils import DownloadError as YDLDownloadError

from remora._internal.ydl.messages import extract_status_code, sanitize_ydl_error
from remora._internal.ydl.types import YDLExtractInfo
from remora._internal.ydl.wrapper import YDL
from remora.exceptions import ExtractorError
from remora.models.search import SearchService, SearchServiceLike


@dataclass(slots=True, frozen=True)
class SearchQuery:
    service: SearchService
    template: str

    def build(self, query: str, limit: int = 20) -> str:
        return self.template.format(limit=limit) + query


SEARCH_QUERIES = {
    SearchQuery(SearchService.SOUNDCLOUD, "scsearch{limit}:"),
    SearchQuery(SearchService.YOUTUBE, "ytsearch{limit}:"),
    SearchQuery(SearchService.YTMUSIC, "https://music.youtube.com/search?q="),
}


def extract_query(
    query: str,
    service: str | SearchServiceLike,
    limit: int = 20,
) -> YDLExtractInfo:
    """Extract info from search service."""

    for item in SEARCH_QUERIES:
        if item.service == service:
            result = extract_info(item.build(query, limit))
            return result

    raise ValueError(f"{service} is invalid. Should be: {SearchService}")


def extract_info(query: str) -> YDLExtractInfo:
    try:
        ydl = YDL(
            params={
                "extract_flat": "in_playlist",
                "skip_download": True,
            },
            auto_init=True,
        )
        info = ydl.extract_info(query, download=False)
    except YDLDownloadError as error:
        raise ExtractorError(
            message=sanitize_ydl_error(error),
            status_code=extract_status_code(error),
        )

    return cast(YDLExtractInfo, info)
