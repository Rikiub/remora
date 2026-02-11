from __future__ import annotations

import bisect
from functools import cached_property
from typing import Generic, Iterator, Literal, overload

from pydantic import OnErrorOmit
from remora.models.base import BaseList
from remora.models.format.codecs import get_codec_rank
from remora.models.format.types import AudioFormat, Format, VideoFormat
from remora.types import FORMAT_TYPE
from typing_extensions import Self, TypeVar, override


def format_sort(format: Format):
    filesize = format.filesize or 0

    if isinstance(format, VideoFormat):
        is_video = 1

        height = format.height
        fps = format.fps or 0

        vcodec = get_codec_rank(format.video_codec, "video")
        acodec = get_codec_rank(format.audio_codec, "audio")

        return (
            is_video,
            height,
            fps,
            vcodec,
            acodec,
            filesize,
        )

    elif isinstance(format, AudioFormat):
        is_video = 0

        bitrate = format.bitrate
        acodec = get_codec_rank(format.audio_codec, "audio")

        return (
            is_video,
            acodec,
            filesize,
            bitrate,
        )


FormatType = OnErrorOmit[VideoFormat | AudioFormat]
F = TypeVar("F", default=Format, bound=Format)


class FormatList(BaseList[FormatType], Generic[F]):
    """List of formats which can be filtered."""

    def filter(
        self,
        extension: str | None = None,
        quality: int | None = None,
        protocol: str | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
    ) -> Self:
        """Get filtered formats by options."""

        items = (f for f in self.root)

        if extension:
            items = (f for f in items if f.extension == extension)
        if quality:
            items = (f for f in items if f.quality == quality)
        if video_codec:
            items = (
                f
                for f in items
                if f.type == "video" and f.video_codec.startswith(video_codec)
            )
        if audio_codec:
            items = (
                f
                for f in items
                if f.type == "audio" and f.audio_codec.startswith(audio_codec)
            )
        if protocol:
            items = (f for f in items if f.protocol == protocol)

        return self.__class__(list(items))

    def only_video(self) -> FormatList[VideoFormat]:
        return FormatList[VideoFormat]([f for f in self.root if f.type == "video"])

    def only_audio(self) -> FormatList[AudioFormat]:
        return FormatList[AudioFormat]([f for f in self.root if f.type == "audio"])

    @cached_property
    def type(self) -> FORMAT_TYPE:
        """
        Determine main format type.
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
        """Sort by `Format` attribute."""

        if attribute == "best":
            filter = format_sort
        elif attribute == "codec":
            filter = lambda codec: get_codec_rank(codec, self.type)  # noqa: E731
        else:
            filter = lambda f: getattr(f, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,  # type: ignore
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> F:
        """Get `Format` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        try:
            format = next(f for f in self if f.id == id)
            return format
        except StopIteration:
            raise IndexError(f"Format with id '{id}' has not been founded")

    def get_closest_quality(self, quality: int) -> F:
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

    @override
    def __iter__(self) -> Iterator[F]:  # type: ignore
        return super().__iter__()  # type: ignore

    @overload
    def __getitem__(self, index: int) -> F: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    @override
    def __getitem__(self, index) -> F | Self:  # type: ignore
        return super().__getitem__(index)
