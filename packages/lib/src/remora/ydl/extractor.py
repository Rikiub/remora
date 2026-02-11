from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError as YDLDownloadError

from remora.exceptions import ExtractError
from remora.types import SEARCH_SERVICE
from remora.ydl.messages import format_except_message
from remora.ydl.types import YDLExtractInfo
from remora.ydl.wrapper import YDL


@dataclass(slots=True)
class SearchQuery:
    service: SEARCH_SERVICE
    template: str

    def build(self, query: str, limit: int = 20) -> str:
        return self.template.format(limit=limit) + query


SEARCH_QUERIES = [
    SearchQuery("soundcloud", "scsearch{limit}:"),
    SearchQuery("youtube", "ytsearch{limit}:"),
    SearchQuery("ytmusic", "https://music.youtube.com/search?q="),
]


def extract_query(
    query: str,
    service: str | SEARCH_SERVICE,
    limit: int = 20,
) -> YDLExtractInfo:
    """Extract info from search service."""

    try:
        result = [item for item in SEARCH_QUERIES if item.service == service]
        result = result[0]
    except IndexError:
        raise ValueError(f"{service} is invalid. Should be: {SEARCH_SERVICE}")

    return extract_info(result.build(query, limit))


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
    except (YDLDownloadError, RequestError) as err:
        msg = format_except_message(err)
        raise ExtractError(msg)

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info.get("extractor_key") == "Generic" and info.get("url") != query:
        if url := info.get("url"):
            return extract_info(url)

    return cast(YDLExtractInfo, info)
