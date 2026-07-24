from pydantic import TypeAdapter

from remora.models.media.item import LazyMedia, Media
from remora.models.media.list import LazyPlaylist, EntriesList, Playlist

LazyExtractResult = LazyMedia | LazyPlaylist
ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

AnyExtractResult = ExtractResult | LazyExtractResult | EntriesList | list[LazyMedia]
