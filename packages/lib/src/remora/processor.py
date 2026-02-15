from typing import Sequence
from anyio import Path
from anyio.to_thread import run_sync

from remora.exceptions import ProcessingError
from remora.models.content.media import Media
from remora.models.metadata.music import Music
from remora.models.stream.types import Stream
from remora.path import get_global_ffmpeg, validate_ffmpeg
from remora.types import AUDIO_EXTENSION, EXTENSION, StrPath
from remora.ydl.processor import RequestedFormat, YDLProcessor
from remora.ydl.types import YDLExtractInfo


class MediaProcessor:
    filepath: Path
    ffmpeg_path: Path | None
    _prc: YDLProcessor

    @classmethod
    async def create(cls, filepath: StrPath, ffmpeg_path: StrPath | None = None):
        self = cls()

        self._prc = YDLProcessor(filepath, ffmpeg_path)
        self.filepath = Path(filepath)

        # Setup FFmpeg
        self.ffmpeg_path = (
            Path(ffmpeg_path) if ffmpeg_path else await get_global_ffmpeg()
        )
        if not self.ffmpeg_path:
            raise ProcessingError("FFmpeg is needed for use processors.")
        await validate_ffmpeg(self.ffmpeg_path)

        return self

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]

    async def change_container(self, format: str | EXTENSION):
        result = await run_sync(self._prc.video_remuxer, format)
        self._update_file(result)
        return self

    async def convert_audio(
        self,
        format: str | AUDIO_EXTENSION | None = None,
        quality: int | None = None,
    ):
        result = await run_sync(self._prc.extract_audio, format, quality)
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

    @classmethod
    async def from_streams_merge(
        cls,
        filepath: StrPath,
        streams: list[tuple[Stream, Path]],
        ffmpeg_path: StrPath | None = None,
    ):
        real_streams: list[RequestedFormat] = []

        for fmt in streams:
            if isinstance(fmt, tuple):
                stream, path = fmt
                stream: Stream
                path: Path

                fmt = {"filepath": str(path)} | stream.to_ydl_dict()
            real_streams.append(fmt)  # type: ignore

        self = await cls.create(filepath, ffmpeg_path)

        result = await run_sync(
            self._prc.from_merger,
            filepath,
            real_streams,
            ffmpeg_path,
        )
        self._update_file(result)

        return self

    def _update_file(self, processor: YDLProcessor):
        self.filepath = Path(processor.filepath)


def _media_to_ydl_music(media: Media, music: Music) -> YDLExtractInfo:
    meta = {}

    # Track
    meta |= {"meta_track": music.track or media.title}

    # Artist
    if media.uploader:
        meta |= {"meta_artist": media.uploader.name}
    if music.artists:
        meta |= {"meta_artist": ", ".join(music.artists)}

    # Album Artist
    if media.uploader:
        meta |= {"meta_album_artist": media.uploader.name}
    if music.album_artists:
        meta |= {"meta_album_artist": ", ".join(music.album_artists)}

    # Year
    if uploaded := media.datetime.uploaded:
        meta |= {"meta_date": str(uploaded.year)}

    return meta
