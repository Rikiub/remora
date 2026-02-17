from __future__ import annotations

import bisect
from functools import cached_property
from typing import Generic, Literal

from pydantic import OnErrorOmit
from typing_extensions import Self, TypeVar

from remora.models._base import BaseList
from remora.models.stream._codecs import get_codec_rank, stream_sort
from remora.models.stream.format import AudioStream, Stream, VideoStream
from remora.types import StreamType

T = TypeVar("T", default=Stream, bound=Stream)


class StreamList(BaseList[OnErrorOmit[T]], Generic[T]):
    """List of streams which can be filtered."""

    def filter(
        self,
        extension: str | None = None,
        quality: int | None = None,
        protocol: str | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
    ) -> Self:
        """Get filtered streams by options."""

        items = (s for s in self.root)

        if extension:
            items = (s for s in items if s.extension == extension)
        if quality:
            items = (s for s in items if s.quality == quality)
        if video_codec:
            items = (
                s
                for s in items
                if isinstance(s, VideoStream) and s.video_codec.startswith(video_codec)
            )
        if audio_codec:
            items = (
                s
                for s in items
                if isinstance(s, AudioStream) and s.audio_codec.startswith(audio_codec)
            )
        if protocol:
            items = (s for s in items if s.protocol == protocol)

        return self.__class__(list(items))

    def only_video(self) -> StreamList[VideoStream]:
        return StreamList[VideoStream](
            [s for s in self.root if isinstance(s, VideoStream)]
        )

    def only_audio(self) -> StreamList[AudioStream]:
        return StreamList[AudioStream](
            [s for s in self.root if isinstance(s, AudioStream)]
        )

    @cached_property
    def type(self) -> StreamType:
        """
        Determine main stream type.
        It will check if is 'video' or 'audio'.
        """

        if self.only_video():
            return "video"
        elif self.only_audio():
            return "audio"
        else:
            return "video"

    def sort_by(
        self,
        attribute: Literal["best", "extension", "quality", "codec", "protocol"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Stream` attribute."""

        if attribute == "best":
            filter = stream_sort
        elif attribute == "codec":
            filter = lambda codec: get_codec_rank(codec, self.type)  # noqa: E731
        else:
            filter = lambda s: getattr(s, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> T:
        """Get `Stream` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        try:
            stream = next(s for s in self if s.id == id)
            return stream
        except StopIteration:
            raise IndexError(f"Stream with id '{id}' has not been founded")

    def get_closest_quality(self, quality: int) -> T:
        items = self.sort_by("quality", reverse=False)
        qualities = [i.quality for i in items]
        pos = bisect.bisect_left(qualities, quality)

        if pos == 0:
            return items[0]
        if pos == len(items):
            return items[-1]

        before, after = items[pos - 1], items[pos]

        if (after.quality - quality) <= (quality - before.quality):
            return after
        else:
            return before
