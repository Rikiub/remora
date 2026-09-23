from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Self

from anyio.to_thread import run_sync

from remora import _ydl
from remora._types import StreamContext
from remora.ffmpeg import get_ffmpeg_dir
from remora.models.container import (
    AudioContainer,
    AVContainer,
    RichAudioContainer,
    RichAVContainer,
    RichVideoContainer,
    VideoContainer,
    get_container,
)
from remora.models.media import Media
from remora.models.metadata import MusicMetadata
from remora.models.stream import StreamQuality
from remora.models.types import StrPath

__all__ = ["MediaProcessor"]


class MediaProcessor:
    def __init__(self, file_path: StrPath, ffmpeg_dir: StrPath | None = None):
        self.file_path = Path(file_path)
        self.file_container: AVContainer
        self.file_extension: str

        # Validate FFmpeg
        self.ffmpeg_dir = get_ffmpeg_dir(ffmpeg_dir)
        self._prc = _ydl.Processor(self.file_path, self.ffmpeg_dir)

        # Sync state
        self._sync(self._prc)

    async def change_container(
        self,
        container: RichAVContainer | AVContainer,
    ) -> Self:
        extension = get_container(container).extension
        result = await run_sync(partial(self._prc.video_remuxer, extension))
        return self._sync(result)

    async def convert_to_audio(
        self,
        container: RichAudioContainer | AudioContainer | None = None,
        quality: StreamQuality | int | None = None,
    ) -> Self:
        container = AudioContainer(container)
        result = await run_sync(
            partial(self._prc.extract_audio, container.extension, quality)
        )
        return self._sync(result)

    async def embed_metadata(self, media: Media) -> Self:
        info = media._to_ydl_dict()
        if media.music:
            info |= _media_to_ydl_music(media, media.music)

        result = await run_sync(partial(self._prc.embed_metadata, info))
        return self._sync(result)

    async def embed_thumbnail(self, thumbnail: StrPath, square: bool = False) -> Self:
        result = await run_sync(partial(self._prc.embed_thumbnail, thumbnail, square))
        return self._sync(result)

    async def embed_subtitles(self, subtitles: Iterable[StrPath]) -> Self:
        result = await run_sync(partial(self._prc.embed_subtitle, subtitles))
        return self._sync(result)

    async def merge_streams(
        self,
        streams: Iterable[StreamContext],
        container: RichVideoContainer | VideoContainer,
    ) -> Self:
        """
        Merge multiple streams in a single file.

        Ensure that `file_path` not exists before run this method.

        Raises:
            FileExistsError: The file path already exists.
        """

        if self.file_path.exists():
            raise FileExistsError(self.file_path)

        # Validate container
        merge_container = get_container(container)
        if isinstance(merge_container, AudioContainer):
            raise TypeError(
                f"'{merge_container}' is a audio-only container. Please select a container with video and audio support."
            )

        # Convert streams to YDL format dict
        real_streams: list[_ydl.RequestedFormat] = []
        for ctx in streams:
            fmt = ctx.stream._to_ydl_dict() | {"filepath": str(ctx.path)}
            real_streams.append(fmt)

        # Start post-processing
        result = await run_sync(
            partial(
                self._prc.merge_formats,
                merge_container.extension,
                real_streams,
            )
        )
        return self._sync(result)

    def _sync(self, processor: _ydl.Processor) -> Self:
        self.file_path = Path(processor.file_path)
        self.file_extension = self.file_path.suffix[1:]

        try:
            self.file_container = get_container(self.file_extension)
        except ValueError:
            raise ValueError(
                f"Unable to determine file container from '{self.file_extension}'"
            )

        return self


def _media_to_ydl_music(media: Media, music: MusicMetadata) -> dict:
    info = {}

    # Track Title
    if title := music.title or media.title:
        info |= {"meta_track": title}

    # Artists
    if artists := music.artists:
        info |= {"meta_artist": ", ".join(artists)}
    elif uploader := media.uploader:
        info |= {"meta_artist": uploader.name}

    # Album Artists
    if artists := music.album_artists:
        info |= {"meta_album_artist": ", ".join(artists)}
    elif uploader := media.uploader:
        info |= {"meta_album_artist": uploader.name}

    # Release Year
    if year := music.year:
        info |= {"meta_year": str(year)}
    elif date := media.date.uploaded:
        info |= {"meta_year": str(date.year)}

    return info
