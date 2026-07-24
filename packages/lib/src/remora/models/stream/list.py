from __future__ import annotations

import bisect
from functools import cached_property
from typing import Annotated, Generic, Literal

from loguru import logger
from pydantic import ValidatorFunctionWrapHandler, WrapValidator
from pydantic_core import PydanticOmit
from typing_extensions import Self, TypeVar

from remora.models._base import BaseList
from remora.models.container.extension.types import ExtensionType
from remora.models.protocol import ProtocolType
from remora.models.stream._filters.rank import get_codec_rank, get_stream_rank
from remora.models.stream.item import (
    AudioStream,
    MuxedStream,
    Stream,
    StreamType,
    VideoStream,
    _DiscriminatedStream,
)
from remora.types import StreamQuality


def _log_and_omit_validator(v, handler: ValidatorFunctionWrapHandler):
    try:
        return handler(v)
    except ValueError:
        id = "unknown"
        is_stream = True

        if isinstance(v, Stream):
            id = v.id
        elif isinstance(v, dict):
            id = v.get("format_id") or v.get("id")

            # Avoid log storyboards
            if v.get("ext") == "mhtml":
                is_stream = False

        if is_stream:
            logger.opt(exception=True).debug('Omiting invalid stream "{}"', id)

        raise PydanticOmit


_LogOnErrorOmit = WrapValidator(_log_and_omit_validator)
T = TypeVar("T", default=_DiscriminatedStream, bound=_DiscriminatedStream)


class StreamList(BaseList[Annotated[T, _LogOnErrorOmit]], Generic[T]):
    """List of streams which can be filtered."""

    def filter(
        self,
        quality: int | StreamQuality | None = None,
        extension: str | ExtensionType | None = None,
        protocol: str | ProtocolType | None = None,
        language: str | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
    ) -> Self:
        """Get filtered streams by options."""

        items = (s for s in self.root)

        if extension:
            items = (s for s in items if s.extension == extension)
        if quality:
            items = (s for s in items if s.quality == quality)
        if protocol:
            items = (s for s in items if s.protocol == protocol)
        if video_codec:
            items = (
                s
                for s in items
                if isinstance(s, VideoStream) and s.video.codec.startswith(video_codec)
            )
        if audio_codec:
            items = (
                s
                for s in items
                if isinstance(s, AudioStream) and s.audio.codec.startswith(audio_codec)
            )
        if language:
            items = (
                s
                for s in items
                if isinstance(s, AudioStream)
                and s.audio.language
                and s.audio.language.startswith(language)
            )

        return self.__class__(list(items))

    def muxed(self) -> StreamList[MuxedStream]:
        """Get strictly muxed streams."""
        return StreamList[MuxedStream](
            [s for s in self.root if isinstance(s, MuxedStream)]
        )

    def videos(self) -> StreamList[VideoStream]:
        """Get all streams that contain video (including muxed streams)."""
        return StreamList[VideoStream](
            [s for s in self.root if isinstance(s, VideoStream)]
        )

    def audios(self) -> StreamList[AudioStream]:
        """Get all streams that contain audio (including muxed streams)."""
        return StreamList[AudioStream](
            [s for s in self.root if isinstance(s, AudioStream)]
        )

    def video_only(self) -> StreamList[VideoStream]:
        """Get strictly video-only streams (excluding muxed streams)."""
        return StreamList[VideoStream]([s for s in self.root if type(s) is VideoStream])

    def audio_only(self) -> StreamList[AudioStream]:
        """Get strictly audio-only streams (excluding muxed streams)."""
        return StreamList[AudioStream]([s for s in self.root if type(s) is AudioStream])

    @cached_property
    def type(self) -> StreamType:
        """
        Determine main stream type.
        It will check if is 'video' or 'audio'.
        """

        if self.videos():
            return "video"
        elif self.audios():
            return "audio"
        else:
            return "video"

    def sorted_by(
        self,
        attribute: Literal[
            "best",
            "extension",
            "quality",
            "protocol",
            "video_codec",
            "audio_codec",
        ],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Stream` attribute."""

        if attribute == "best":
            filter = get_stream_rank
        elif attribute == "video_codec":
            filter = lambda codec: get_codec_rank(codec, "video")  # noqa: E731
        elif attribute == "audio_codec":
            filter = lambda codec: get_codec_rank(codec, "audio")  # noqa: E731
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
            KeyError: Provided id has not been founded.
        """

        try:
            stream = next(s for s in self if s.id == id)
            return stream
        except StopIteration:
            raise KeyError(f"Stream with id '{id}' has not been found")

    def get_closest_quality(self, quality: int) -> T:
        if not self.root:
            raise ValueError("Cannot find closest quality in an empty list")

        items = self.sorted_by("quality", reverse=False)
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
