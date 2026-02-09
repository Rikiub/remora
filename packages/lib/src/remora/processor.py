from pathlib import Path

from typing_extensions import override

from remora.models.content.media import Media
from remora.models.format.types import Format
from remora.types import AUDIO_EXTENSION, EXTENSION, StrPath
from remora.ydl.processor import (
    RequestedFormat,
    RequestedFormats,
    YDLProcessor,
)
from remora.ydl.types import YDLExtractInfo

FormatPaths = list[tuple[Format, Path]]


class MediaProcessor(YDLProcessor):
    @override
    async def change_container(self, format: str | EXTENSION):
        return await super().change_container(format)

    @override
    async def convert_audio(
        self,
        format: str | AUDIO_EXTENSION = "",
        quality: int | None = None,
    ):
        return await super().convert_audio(format, quality)

    @override
    async def embed_metadata(
        self,
        data: YDLExtractInfo | Media,
        include_music: bool = False,
    ):
        if isinstance(data, Media):
            info = data.to_ydl_dict()
            if include_music:
                info |= _media_to_music_metadata(data)
        else:
            info = data

        await super().embed_metadata(info)
        return self

    @override
    @classmethod
    async def from_formats_merge(
        cls,
        filepath: StrPath,
        formats: RequestedFormats | FormatPaths,
        ffmpeg_path: StrPath | None = None,
    ):
        real_formats: list[RequestedFormat] = []

        for fmt in formats:
            if isinstance(fmt, tuple):
                format, path = fmt
                format: Format
                path: Path

                fmt = {"filepath": str(path)} | format.to_ydl_dict()
            real_formats.append(fmt)  # type: ignore

        cls = await super().from_formats_merge(
            filepath,
            formats=real_formats,
            ffmpeg_path=ffmpeg_path,
        )
        return cls


def _media_to_music_metadata(media: Media) -> YDLExtractInfo:
    return {
        "meta_track": media.track or media.title,
        "meta_artist": ", ".join(media.artists) if media.artists else media.uploader,
        "meta_album_artist": media.album_artist or media.uploader,
        "meta_date": str(media.datetime.year) if media.datetime else "",
    }
