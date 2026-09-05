from collections.abc import Sequence

from pydantic import TypeAdapter

from remora.models.media._base import Extractor
from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, Playlist, SearchList

__all__ = [
    "AnyExtractResult",
    "ExtractAdapter",
    "ExtractResult",
    "Extractor",
    "LazyExtractResult",
]

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
AnyExtractResult = LazyExtractResult | ExtractResult | SearchList | Sequence[LazyMedia]

ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)
