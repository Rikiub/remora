from __future__ import annotations

import bisect
from typing import Annotated, Generic, Literal, Self

from loguru import logger
from pydantic import ValidatorFunctionWrapHandler, WrapValidator
from pydantic_core import PydanticOmit
from typing_extensions import TypeVar

from remora.models._base import BaseList, FilterValue, to_tuple
from remora.models.container import (
    AudioCodec,
    AVContainerLike,
    VideoCodec,
    get_container,
)
from remora.models.protocol import Protocol, ProtocolLike
from remora.models.rank import get_codec_rank, get_stream_rank
from remora.models.stream import AudioInfo, VideoInfo
from remora.models.stream.item import (
    AudioStream,
    MuxedStream,
    Stream,
    StreamQuality,
    VideoStream,
    _DiscriminatedStream,
)

__all__ = ["StreamList"]


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
_Stream = TypeVar("_Stream", default=_DiscriminatedStream, bound=_DiscriminatedStream)


class StreamList(BaseList[Annotated[_Stream, _LogOnErrorOmit]], Generic[_Stream]):
    """List of streams which can be filtered."""

    def filter(
        self,
        quality: FilterValue[StreamQuality | int] = None,
        container: FilterValue[AVContainerLike] = None,
        protocol: FilterValue[ProtocolLike] = None,
        video_codec: FilterValue[VideoCodec] = None,
        audio_codec: FilterValue[AudioCodec] = None,
        language: FilterValue[str] = None,
    ) -> Self:
        """Get filtered streams by options."""

        items = (s for s in self.root)

        if container:
            values = {get_container(i) for i in to_tuple(container)}
            items = (s for s in items if s.container in values)
        if quality:
            values = to_tuple(quality)
            items = (s for s in items if s.quality in values)
        if protocol:
            values = {Protocol(i) for i in to_tuple(protocol)}
            items = (s for s in items if s.protocol in values)
        if video_codec:
            values = to_tuple(video_codec)
            items = (
                s
                for s in items
                if isinstance(s, VideoStream)
                and (codec := s.video.codec)
                and (
                    codec.normalized.startswith(values)
                    or codec.original.startswith(values)
                )
            )
        if audio_codec:
            values = to_tuple(audio_codec)
            items = (
                s
                for s in items
                if isinstance(s, AudioStream)
                and (codec := s.audio.codec)
                and (
                    codec.normalized.startswith(values)
                    or codec.original.startswith(values)
                )
            )
        if language:
            values: tuple[str, ...] = to_tuple(language)  # ty: ignore[invalid-assignment]
            items = (
                s
                for s in items
                if isinstance(s, AudioStream)
                and s.audio.language
                and s.audio.language.startswith(values)
            )

        return self.__class__(list(items))

    def muxed(self) -> StreamList[MuxedStream]:
        """Get strictly muxed streams."""
        return StreamList[MuxedStream](
            s for s in self.root if isinstance(s, MuxedStream)
        )

    def videos(self) -> StreamList[VideoStream]:
        """Get all streams that contain video (including muxed streams)."""
        return StreamList[VideoStream](
            s for s in self.root if isinstance(s, VideoStream)
        )

    def audios(self) -> StreamList[AudioStream]:
        """Get all streams that contain audio (including muxed streams)."""
        return StreamList[AudioStream](
            s for s in self.root if isinstance(s, AudioStream)
        )

    def video_only(self) -> StreamList[VideoStream]:
        """Get strictly video-only streams (excluding muxed streams)."""
        return StreamList[VideoStream](s for s in self.root if type(s) is VideoStream)

    def audio_only(self) -> StreamList[AudioStream]:
        """Get strictly audio-only streams (excluding muxed streams)."""
        return StreamList[AudioStream](s for s in self.root if type(s) is AudioStream)

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
            filter = lambda codec: get_codec_rank(VideoInfo(codec=codec))
        elif attribute == "audio_codec":
            filter = lambda codec: get_codec_rank(AudioInfo(codec=codec))
        else:
            filter = lambda s: getattr(s, attribute)

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> _Stream:
        """Get `Stream` by `id`.

        Raises:
            KeyError: Provided id has not been founded.
        """

        try:
            stream = next(s for s in self if s.id == id)
            return stream
        except StopIteration:
            raise KeyError(f"Stream with id '{id}' has not been found")

    def get_closest_quality(self, quality: int) -> _Stream:
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
