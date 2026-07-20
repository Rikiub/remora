from __future__ import annotations

import bisect
from functools import cached_property
from typing import Annotated, Generic, Literal

from loguru import logger
from pydantic import ValidationError, ValidatorFunctionWrapHandler, WrapValidator
from pydantic_core import PydanticOmit
from typing_extensions import Self, TypeVar

from remora.models._base import BaseList
from remora.models.format.extension import ExtensionType
from remora.models.format.protocol import ProtocolType
from remora.models.format.type import FormatKind, FormatType
from remora.models.stream._sort import get_codec_rank, get_stream_rank
from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.types import StreamQuality


def _log_and_omit_validator(v, handler: ValidatorFunctionWrapHandler):
    try:
        return handler(v)
    except ValidationError:
        logger.opt(exception=True).debug(
            'Omiting invalid stream "{}"',
            v.get("format_id") or v.get("id") or "unkdown",
        )
        raise PydanticOmit


T = TypeVar("T", default=Stream, bound=Stream)
_LogOnErrorOmit = WrapValidator(_log_and_omit_validator)


class StreamList(BaseList[Annotated[T, _LogOnErrorOmit]], Generic[T]):
    """List of streams which can be filtered."""

    def filter(
        self,
        quality: int | StreamQuality | None = None,
        extension: str | ExtensionType | None = None,
        protocol: str | ProtocolType | None = None,
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
                if isinstance(s, VideoStream) and s.codec.startswith(video_codec)
            )
        if audio_codec:
            items = (
                s
                for s in items
                if isinstance(s, AudioStream) and s.codec.startswith(audio_codec)
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
    def type(self) -> FormatType:
        """
        Determine main stream type.
        It will check if is 'video' or 'audio'.
        """

        if self.only_video():
            return FormatKind.VIDEO
        elif self.only_audio():
            return FormatKind.AUDIO
        else:
            return FormatKind.VIDEO

    def sort_by(
        self,
        attribute: Literal["best", "extension", "quality", "codec", "protocol"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Stream` attribute."""

        if attribute == "best":
            filter = get_stream_rank
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
