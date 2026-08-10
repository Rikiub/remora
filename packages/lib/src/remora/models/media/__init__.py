from collections.abc import Iterable

from pydantic import TypeAdapter

from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import EntriesList, LazyPlaylist, Playlist, SearchList

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

AnyExtractResult = (
    LazyExtractResult | ExtractResult | SearchList | EntriesList | Iterable[LazyMedia]
)

__all__ = [
    "AnyExtractResult",
    "EntriesList",
    "ExtractResult",
    "LazyExtractResult",
    "LazyMedia",
    "LazyPlaylist",
    "Media",
    "Playlist",
    "SearchList",
]
