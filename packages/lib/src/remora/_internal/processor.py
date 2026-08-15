from collections.abc import Sequence
from pathlib import Path
from typing import Self

from anyio.to_thread import run_sync

from remora._internal.ffmpeg import get_ffmpeg
from remora._internal.types import StreamContext
from remora._internal.ydl.processor import RequestedFormat, YDLProcessor
from remora._internal.ydl.types import YDLExtractInfo
from remora.models.container import (
    AVContainer,
    RichAudioContainer,
    RichAVContainer,
)
from remora.models.media import Media
from remora.models.metadata import MusicMetadata
from remora.models.stream import AudioStream, VideoStream
from remora.types import AudioQuality, StrPath


class MediaProcessor:
    def __init__(self, file_path: StrPath, ffmpeg_path: StrPath | None = None):
        self.file_path = Path(file_path)

        # Validate FFmpeg
        self.ffmpeg_path = get_ffmpeg(ffmpeg_path)
        self._prc = YDLProcessor(self.file_path, self.ffmpeg_path)

    @property
    def extension(self) -> str:
        return self.file_path.suffix[1:]

    async def change_container(self, container: RichAVContainer | AVContainer) -> Self:
        result = await run_sync(self._prc.video_remuxer, str(container))
        self._update_file(result)
        return self

    async def convert_audio(
        self,
        container: RichAudioContainer | AVContainer | None = None,
        quality: AudioQuality | None = None,
    ) -> Self:
        result = await run_sync(self._prc.extract_audio, str(container), quality)
        self._update_file(result)
        return self

    async def embed_metadata(self, media: Media) -> Self:
        info = media._to_ydl_dict()
        if media.music:
            info |= _media_to_ydl_music(media, media.music)

        result = await run_sync(self._prc.embed_metadata, info)
        self._update_file(result)
        return self

    async def embed_thumbnail(self, thumbnail: StrPath, square: bool = False) -> Self:
        result = await run_sync(self._prc.embed_thumbnail, thumbnail, square)
        self._update_file(result)
        return self

    async def embed_subtitles(self, subtitles: Sequence[StrPath]) -> Self:
        result = await run_sync(self._prc.embed_subtitle, subtitles)
        self._update_file(result)
        return self

    async def merge_streams(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
        merge_container: RichAVContainer | AVContainer,
    ) -> Self:
        """
        Merge two streams in a single file (Remuxing).

        Ensure that `file_path` not exists before run this method.

        Raises:
            FileExistsError: The file path already exists.
        """

        merge_container = AVContainer(merge_container)
        if merge_container.is_audio_only:
            raise ValueError(
                f"'{merge_container}' is a audio-only container. Please select a container with video and audio support."
            )

        real_streams: list[RequestedFormat] = []
        for ctx in (video, audio):
            fmt = {"filepath": str(ctx.path)} | ctx.stream._to_ydl_dict()
            real_streams.append(fmt)  # type: ignore

        result = await run_sync(
            self._prc.merge_formats, str(merge_container), real_streams
        )
        self._update_file(result)
        return self

    def _update_file(self, processor: YDLProcessor):
        self.file_path = Path(processor.file_path)


def _media_to_ydl_music(media: Media, music: MusicMetadata) -> YDLExtractInfo:
    meta = {}

    # Track
    title = music.track or media.title
    if title:
        meta |= {"meta_track": title}

    # Artist
    if music.artists:
        meta |= {"meta_artist": ", ".join(music.artists)}
    elif media.uploader:
        meta |= {"meta_artist": media.uploader.name}

    # Album Artist
    if music.album_artists:
        meta |= {"meta_album_artist": ", ".join(music.album_artists)}
    elif media.uploader:
        meta |= {"meta_album_artist": media.uploader.name}

    # Year
    if media.upload_date:
        meta |= {"meta_date": str(media.upload_date.year)}

    return meta
