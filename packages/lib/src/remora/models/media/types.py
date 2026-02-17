from pydantic import TypeAdapter

from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, MediaList, Playlist

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

AnyExtractResult = ExtractResult | LazyExtractResult | MediaList | list[LazyMedia]
