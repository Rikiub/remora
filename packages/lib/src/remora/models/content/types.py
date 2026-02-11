from pydantic import TypeAdapter
from remora.models.content.list import LazyPlaylist, Playlist
from remora.models.content.media import LazyMedia, Media

ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

MediaListEntries = LazyMedia | LazyPlaylist
MediaListAdapter = TypeAdapter[MediaListEntries](MediaListEntries)
