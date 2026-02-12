from typing import TypeVar, cast

from remora.downloader.config import FormatConfig
from remora.models.content.media import Media
from remora.models.stream.list import StreamList
from remora.models.stream.types import AudioStream, Stream, VideoStream

T = TypeVar("T", bound=Stream)


class StreamSelector:
    """Responsible for selecting the best video/audio formats based on config."""

    def __init__(self, config: FormatConfig):
        self._config = config

    def resolve(self, media: Media) -> tuple[VideoStream | None, AudioStream | None]:
        """Resolves the final pair of formats to be downloaded."""
        audio = self.extract_best(media.streams, AudioStream)

        if audio and (media.is_music or self._config.type == "audio"):
            return None, audio

        video = self.extract_best(media.streams, VideoStream)
        return video, audio

    def extract_best(self, streams: StreamList, type: type[T]) -> T | None:
        # Get type
        candidates = (
            streams.only_video()
            if issubclass(type, VideoStream)
            else streams.only_audio()
        )

        if not candidates:
            return None

        # Filter by extension
        if self._config.convert:
            if filtered := candidates.filter(extension=self._config.convert):
                candidates = filtered

        if self._config.quality:
            # Resolve Quality
            result = candidates.get_closest_quality(self._config.quality)
        else:
            result = candidates[0]

        return cast(T, result)
