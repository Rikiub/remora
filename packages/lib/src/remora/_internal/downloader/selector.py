from dataclasses import dataclass
from typing import TypeVar, cast

from remora.models.download_options import DownloadOptions
from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, MuxedStream, Stream, VideoStream
from remora.models.stream.list import StreamList


@dataclass(slots=True)
class SelectorContext:
    muxed: MuxedStream | None = None
    video: VideoStream | None = None
    audio: AudioStream | None = None

    def __bool__(self) -> bool:
        return bool(self.muxed or self.video or self.audio)


_T = TypeVar("_T", bound=Stream)


class StreamSelector:
    """Responsible for selecting the best video/audio streams based on config."""

    def __init__(self, config: DownloadOptions):
        self.config = config

    def resolve(self, media: Media) -> SelectorContext:
        """Resolves the final pair of streams to be downloaded."""
        audio = self.extract_best(media.streams, AudioStream)

        if audio and (media.music or self.config.format_type == "audio"):
            return SelectorContext(audio=audio)

        video = self.extract_best(media.streams, VideoStream)
        return SelectorContext(video=video, audio=audio)

    def extract_best(self, streams: StreamList, type: type[_T]) -> _T | None:
        # Get type
        candidates = (
            streams.videos() if issubclass(type, VideoStream) else streams.audio_only()
        )

        if not candidates:
            return None

        # Filter by extension
        if self.config.convert_to and (
            filtered := candidates.filter(extension=self.config.convert_to)
        ):
            candidates = filtered

        if self.config.quality:
            # Resolve Quality
            result = candidates.get_closest_quality(self.config.quality)
        else:
            result = candidates[0]

        return cast(_T, result)
