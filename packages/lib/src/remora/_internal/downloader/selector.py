from typing import TypeVar, cast

from remora.models.download_options import DownloadOptions
from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.models.stream.list import StreamList

T = TypeVar("T", bound=Stream)


class StreamSelector:
    """Responsible for selecting the best video/audio streams based on config."""

    def __init__(self, config: DownloadOptions):
        self.config = config

    def resolve(self, media: Media) -> tuple[VideoStream | None, AudioStream | None]:
        """Resolves the final pair of streams to be downloaded."""
        audio = self.extract_best(media.streams, AudioStream)

        if audio and (media.music or self.config.format_type == "audio"):
            return None, audio

        video = self.extract_best(media.streams, VideoStream)
        return video, audio

    def extract_best(self, streams: StreamList, type: type[T]) -> T | None:
        # Get type
        candidates = (
            streams.videos() if issubclass(type, VideoStream) else streams.audio_only()
        )

        if not candidates:
            return None

        # Filter by extension
        if self.config.format_target:
            if filtered := candidates.filter(extension=self.config.format_target):
                candidates = filtered

        if self.config.quality:
            # Resolve Quality
            result = candidates.get_closest_quality(self.config.quality)
        else:
            result = candidates[0]

        return cast(T, result)
