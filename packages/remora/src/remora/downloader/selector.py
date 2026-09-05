from typing import TypeVar, cast

from remora.constants import DEFAULT_STREAM_LANGUAGE
from remora.models.media import Media
from remora.models.options.download import DownloadOptions
from remora.models.rank import get_audio_rank, get_video_rank
from remora.models.stream import (
    AudioStream,
    MuxedStream,
    Stream,
    StreamList,
    VideoStream,
)

__all__ = ["StreamSelector"]
_T = TypeVar("_T", bound=Stream)


class StreamSelector:
    """Responsible for selecting the best video/audio streams based on options."""

    def __init__(
        self,
        download_options: DownloadOptions | None = None,
        merge_available: bool = True,
    ):
        self.download_options = download_options or DownloadOptions()
        self.merge_available = merge_available

    def resolve(self, media: Media) -> list[Stream]:
        """Resolves the final pair of streams to be downloaded.

        When merging is available, the best separate video and audio streams
        are preferred only if both are strictly better than the best muxed
        stream. Otherwise, the complete muxed stream is preferred.
        """
        streams = media.streams.sorted_by("best")

        muxed = self._extract_best(streams, MuxedStream)
        video = self._extract_best(streams, VideoStream)
        audio = self._extract_best(streams, AudioStream)

        if audio and (
            (media._is_audio_only or self.download_options.format_type == "audio")
            or not (video or muxed)
        ):
            return [audio]

        if (
            self.merge_available
            and video
            and audio
            and (
                not muxed
                or not self._is_muxed_better(
                    muxed=muxed,
                    video=video,
                    audio=audio,
                )
            )
        ):
            results = [video]

            if prefered_audios := self._extract_prefered_audios(streams):
                results.extend(prefered_audios)
            else:
                results.append(audio)

            return results

        if muxed:
            return [muxed]
        if video:
            return [video]

        raise ValueError("Unable to determine best streams")

    def _extract_prefered_audios(self, streams: StreamList) -> list[AudioStream]:
        candidates = []

        if langs := self.download_options.languages:
            audio_streams = streams.audio_only()

            for lang in langs:
                if (audios := audio_streams.filter(language=lang)) and (
                    result := self._extract_best(
                        audios,  # ty: ignore[invalid-argument-type]
                        AudioStream,
                    )
                ):
                    candidates.append(result)

        return list(candidates)

    def _extract_best(self, streams: StreamList, type: type[_T]) -> _T | None:
        # Filter candidates
        if type is MuxedStream:
            candidates = streams.muxed()
        elif type is VideoStream:
            candidates = streams.video_only()
        elif type is AudioStream:
            candidates = streams.audio_only()
        else:
            raise TypeError(f"Unsupported stream type: {type}")

        if (values := candidates.filter(language=self.download_options.languages)) or (
            values := candidates.filter(language=DEFAULT_STREAM_LANGUAGE)
        ):
            candidates = values

        if not candidates:
            return None

        # Map to FormatType
        literal_type = {
            MuxedStream: "video",
            VideoStream: "video",
            AudioStream: "audio",
        }[type]

        # Get final result
        if self.download_options.quality and (
            # If format type is declared, then filter only that type
            self.download_options.format_type == literal_type
            # If format type isn't declared, then default to filter only videos
            or issubclass(type, VideoStream)
        ):
            # Resolved quality
            result = candidates.get_closest_quality(self.download_options.quality)
        else:
            # Default result
            result = candidates[0]

        return cast(_T, result)

    def _is_muxed_better(
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
