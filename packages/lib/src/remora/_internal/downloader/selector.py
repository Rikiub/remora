from dataclasses import dataclass
from typing import TypeVar, cast

from remora.models.download_options import DownloadOptions
from remora.models.media.item import Media
from remora.models.stream._filters.rank import get_codec_rank
from remora.models.stream.item import (
    AudioStream,
    MuxedStream,
    Stream,
    VideoStream,
)
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

    def __init__(self, config: DownloadOptions, merge_available: bool = True):
        self.config = config
        self.merge_available = merge_available

    def resolve(self, media: Media) -> SelectorContext:
        """Resolves the final pair of streams to be downloaded.

        When merging is available, the best separate video and audio streams
        are preferred only if both are strictly better than the best muxed
        stream. Otherwise, the complete muxed stream is preferred.
        """
        muxed = self.extract_best(media.streams, MuxedStream)
        audio = self.extract_best(media.streams, AudioStream)

        if audio and (media._is_audio_only or self.config.format_type == "audio"):
            return SelectorContext(audio=audio)

        video = self.extract_best(media.streams, VideoStream)

        if (
            self.merge_available
            and video
            and audio
            and (not muxed or self._is_pair_better(video, audio, muxed))
        ):
            return SelectorContext(video=video, audio=audio)

        if muxed:
            return SelectorContext(muxed=muxed)

        return SelectorContext(video=video, audio=audio)

    def extract_best(self, streams: StreamList, type: type[_T]) -> _T | None:
        # Get type
        if type is MuxedStream:
            candidates = streams.muxed()
        elif type is VideoStream:
            candidates = streams.video_only()
        elif type is AudioStream:
            candidates = streams.audio_only()
        else:
            raise TypeError(f"Unsupported stream type: {type}")

        if not candidates:
            return None

        # Filter by extension
        """
        if self.config.convert_to and (
            filtered := candidates.filter(extension=self.config.convert_to)
        ):
            candidates = filtered
        """

        # Default candidate
        result = candidates[0]

        # Map to FormatType
        literal_type = {
            MuxedStream: "muxed",
            VideoStream: "video",
            AudioStream: "audio",
        }[type]

        # Resolve quality
        if (
            # If format type is declared, then filter only that type
            self.config.quality
            and (f := self.config.format_type)
            and f.startswith(literal_type)
            # If format type isn't declared, then default to filter only videos
            or self.config.quality
            and isinstance(type, VideoStream)
        ):
            result = candidates.get_closest_quality(self.config.quality)

        return cast(_T, result)

    def _is_pair_better(
        self,
        video: VideoStream,
        audio: AudioStream,
        muxed: MuxedStream,
    ) -> bool:
        """Checks if the separate pair is better than the complete muxed stream."""
        return bool(
            _video_rank(video) > _video_rank(muxed)
            and _audio_rank(audio) > _audio_rank(muxed)
        )


def _video_rank(stream: VideoStream) -> tuple[float, ...]:
    """Rank the video part of a stream to compare quality between types."""
    video = stream.video

    return (
        video.resolution.height if video.resolution else 0,
        video.fps or 0,
        get_codec_rank(video.codec, "video"),
    )


def _audio_rank(stream: AudioStream) -> tuple[float, ...]:
    """Rank the audio part of a stream to compare quality between types."""
    audio = stream.audio

    return (
        audio.channels or 0,
        audio.bitrate or 0,
        get_codec_rank(audio.codec, "audio"),
        audio.sample_rate or 0,
    )
