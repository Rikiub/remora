from pathlib import Path

from typing_extensions import override

from remora.models.content.media import Media
from remora.models.stream.types import Stream
from remora.types import AUDIO_EXTENSION, EXTENSION, StrPath
from remora.ydl.processor import (
    RequestedFormat,
    RequestedFormats,
    YDLProcessor,
)
from remora.ydl.types import YDLExtractInfo

StreamPaths = list[tuple[Stream, Path]]


class MediaProcessor(YDLProcessor):
    @override
    async def change_container(self, stream: str | EXTENSION):
        return await super().change_container(stream)

    @override
    async def convert_audio(
        self,
        stream: str | AUDIO_EXTENSION = "",
        quality: int | None = None,
    ):
        return await super().convert_audio(stream, quality)

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
    async def from_streams_merge(
        cls,
        filepath: StrPath,
        streams: RequestedFormats | StreamPaths,
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

        cls = await super().from_streams_merge(
            filepath,
            streams=real_streams,
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
