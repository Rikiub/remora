from collections.abc import Sequence

from pydantic import TypeAdapter

from remora.models.media._base import Extractor
from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import EntriesList, LazyPlaylist, Playlist, SearchList

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
_ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

AnyExtractResult = LazyExtractResult | ExtractResult | SearchList | Sequence[LazyMedia]

__all__ = [
    "AnyExtractResult",
    "EntriesList",
    "ExtractResult",
    "Extractor",
    "LazyExtractResult",
    "LazyMedia",
    "LazyPlaylist",
    "Media",
    "Playlist",
    "SearchList",
]
