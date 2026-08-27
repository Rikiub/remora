from dataclasses import dataclass
from typing import TypeVar, cast

from remora.models.download_options import DownloadOptions
from remora.models.media import Media
from remora.models.rank import get_audio_rank, get_video_rank
from remora.models.stream import (
    AudioStream,
    MuxedStream,
    Stream,
    StreamList,
    VideoStream,
)


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
            and (
                not muxed
                or not self.is_muxed_better(
                    muxed=muxed,
                    video=video,
                    audio=audio,
                )
            )
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

        # Default candidate
        result = candidates[0]

        # Map to FormatType
        literal_type = {
            MuxedStream: "video",
            VideoStream: "video",
            AudioStream: "audio",
        }[type]

        # Resolve quality
        if self.config.quality and (
            # If format type is declared, then filter only that type
            self.config.format_type == literal_type
            # If format type isn't declared, then default to filter only videos
            or issubclass(type, VideoStream)
        ):
            result = candidates.get_closest_quality(self.config.quality)

        return cast(_T, result)

    def is_muxed_better(
        self,
        muxed: MuxedStream,
        video: VideoStream,
        audio: AudioStream,
    ) -> bool:
        """Checks if the complete muxed stream is better than the separate pair."""
        return bool(
            get_video_rank(muxed.video) > get_video_rank(video.video)
            and get_audio_rank(muxed.audio) > get_audio_rank(audio.audio)
        )
