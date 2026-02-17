from pydantic import TypeAdapter

from remora.models.content.list import LazyPlaylist, MediaList, Playlist
from remora.models.content.media import LazyMedia, Media

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

AnyExtractResult = ExtractResult | LazyExtractResult | MediaList | list[LazyMedia]
