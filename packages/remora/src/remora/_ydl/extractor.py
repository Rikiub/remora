from dataclasses import dataclass
from typing import cast

from yt_dlp.extractor import get_info_extractor
from yt_dlp.utils import DownloadError as YDLDownloadError
from yt_dlp.utils._utils import determine_protocol

from remora._ydl.messages import extract_status_code, sanitize_ydl_error
from remora._ydl.session import YDL, YDLDict, YDLSession
from remora.exceptions import ExtractorError
from remora.models.search import SearchService

__all__ = ["YDLExtractor"]


@dataclass(slots=True, frozen=True)
class SearchQuery:
    service: SearchService
    template: str

    def build(self, query: str, limit: int = 25) -> str:
        return self.template.format(limit=limit) + query


SEARCH_QUERIES = {
    SearchQuery("soundcloud", "scsearch{limit}:"),
    SearchQuery("youtube", "ytsearch{limit}:"),
    SearchQuery("ytmusic", "https://music.youtube.com/search?q="),
}


class YDLExtractor:
    def __init__(self, session: YDLSession):
        self.session = session
        self._ydl = YDL(
            params={"extract_flat": "in_playlist", "skip_download": True},
            session=session,
            auto_init=True,
        )

    def extract_query(
        self,
        query: str,
        service: str | SearchService,
        limit: int = 20,
    ) -> YDLDict:
        """Extract info from search service."""

        for item in SEARCH_QUERIES:
            if item.service == service:
                result = self.extract_info(item.build(query, limit))
                return result

        raise ValueError(f"{service} is invalid. Should be: {SearchService}")

    def extract_info(self, query: str) -> YDLDict:
        try:
            info = self._ydl.extract_info(query, download=False)
            info = self._normalize_info(info)

            # Infer protocol if missing
            if info.get("url"):
                info["protocol"] = determine_protocol(info)
        except YDLDownloadError as error:
            raise ExtractorError(
                message=sanitize_ydl_error(error),
                status_code=extract_status_code(error),
            )

        return cast(YDLDict, info)

    def _normalize_info(self, info: dict) -> dict:
        # Normalize the current level extractor fields
        info = self._normalize_extractor_field(info)

        # Recursively normalize all children
        if entries := info.get("entries"):
            # Only recurse if `entry` is an actual dictionary.
            info["entries"] = [
                self._normalize_info(entry) if entry else entry for entry in entries
            ]

        return info

    def _normalize_extractor_field(self, info: dict) -> dict:
        extractor = get_info_extractor(info.get("extractor_key") or info.get("ie_key"))
        info["extractor_key"] = extractor.ie_key()
        info["extractor"] = extractor.IE_NAME
        info.pop("ie_key", None)
        return info
