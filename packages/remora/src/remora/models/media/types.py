from collections.abc import Sequence

from pydantic import TypeAdapter

from remora.models.media._base import ExtractorInfo
from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, Playlist, SearchList

__all__ = [
    "AnyExtractResult",
    "ExtractAdapter",
    "ExtractResult",
    "ExtractorInfo",
    "LazyExtractResult",
]

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
AnyExtractResult = LazyExtractResult | ExtractResult | SearchList | Sequence[LazyMedia]

ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)
