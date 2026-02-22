from collections.abc import Sequence
from pathlib import Path

from anyio.to_thread import run_sync

from remora._internal.path import get_ffmpeg
from remora._internal.types.audio import AudioExtensionLike
from remora._internal.types.extension import StreamExtensionLike
from remora._internal.types.video import VideoExtensionLike
from remora._internal.ydl.processor import RequestedFormat, YDLProcessor
from remora._internal.ydl.types import YDLExtractInfo
from remora.exceptions import FFmpegNotFoundError
from remora.models.media.item import Media
from remora.models.metadata.music import MusicMetadata
from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.types import StrPath


class MediaProcessor:
    def __init__(self, file_path: StrPath, ffmpeg_path: StrPath | None = None):
        self.file_path = Path(file_path)

        # Validate FFmpeg
        try:
            ffmpeg_path = get_ffmpeg(ffmpeg_path)
        except FileNotFoundError as e:
            raise FFmpegNotFoundError(str(e)) from e

        if not self.file_path.is_file():
            raise FileNotFoundError(f'"{self.file_path.name}" not is a file.')

        # Set ffmpeg
        self.ffmpeg_path = Path(ffmpeg_path)
        self._prc = YDLProcessor(self.file_path, self.ffmpeg_path)

    @property
    def extension(self) -> str:
        return self.file_path.suffix[1:]

    async def change_container(self, format: str | StreamExtensionLike):
        result = await run_sync(self._prc.video_remuxer, str(format))
        self._update_file(result)
        return self

    async def convert_audio(
        self,
        format: str | AudioExtensionLike | None = None,
        quality: int | None = None,
    ):
        result = await run_sync(self._prc.extract_audio, str(format), quality)
        self._update_file(result)
        return self

    async def embed_metadata(self, media: Media):
        info = media.to_ydl_dict()
        if media.music:
            info |= _media_to_ydl_music(media, media.music)

        result = await run_sync(self._prc.embed_metadata, info)
        self._update_file(result)
        return self

    async def embed_thumbnail(self, thumbnail: StrPath, square: bool = False):
        result = await run_sync(self._prc.embed_thumbnail, thumbnail, square)
        self._update_file(result)
        return self

    async def embed_subtitles(self, subtitles: Sequence[StrPath]):
        result = await run_sync(self._prc.embed_subtitle, subtitles)
        self._update_file(result)
        return self

    async def merge_streams(
        self,
        video: tuple[VideoStream, Path],
        audio: tuple[AudioStream, Path],
        merge_format: VideoExtensionLike,
    ):
        real_streams: list[RequestedFormat] = []

        for fmt in (video, audio):
            if isinstance(fmt, tuple):
                stream, path = fmt

                stream: Stream
                path: Path

                fmt = {"filepath": str(path)} | stream.to_ydl_dict()
            real_streams.append(fmt)  # type: ignore

        result = await run_sync(
            self._prc.merge_formats, str(merge_format), real_streams
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
