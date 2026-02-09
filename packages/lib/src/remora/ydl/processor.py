import asyncio
from pathlib import Path
from typing import Sequence, TypedDict

from typing_extensions import Self
from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP
from yt_dlp.postprocessor.ffmpeg import (
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegMergerPP,
    FFmpegMetadataPP,
    FFmpegPostProcessorError,
    FFmpegVideoRemuxerPP,
)

from remora.exceptions import ProcessingError
from remora.path import get_ffmpeg
from remora.types import StrPath
from remora.ydl.types import YDLExtractInfo


def catch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FFmpegPostProcessorError as e:
            raise ProcessingError(str(e))

    return wrapper


class RequestedFormat(TypedDict):
    filepath: str
    vcodec: str
    acodec: str


RequestedFormats = list[RequestedFormat]


class YDLProcessor:
    def __init__(self, filepath: StrPath, ffmpeg_path: StrPath | None = None) -> None:
        self.filepath = Path(filepath)

        if not self.extension:
            raise ValueError(f'"{self.filepath}" must have a file extension.')

        self.ffmpeg_path = get_ffmpeg(ffmpeg_path)
        if not self.ffmpeg_path:
            raise ProcessingError("FFmpeg is needed for use postprocessors.")

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]

    @catch
    async def change_container(self, format: str) -> Self:
        pp = FFmpegVideoRemuxerPP(
            None,
            preferedformat=format,
        )
        _, data = await asyncio.to_thread(pp.run, self.params)
        self._update_filepath(data)
        return self

    @catch
    async def convert_audio(
        self,
        format: str = "",
        quality: int | None = None,
    ) -> Self:
        pp = FFmpegExtractAudioPP(
            None,
            nopostoverwrites=False,
            preferredcodec=format,
            preferredquality=quality,
        )

        _, data = await asyncio.to_thread(pp.run, self.params)
        self._update_filepath(data)
        return self

    @catch
    async def embed_metadata(self, data: YDLExtractInfo):
        pp = FFmpegMetadataPP(
            None,
            add_metadata=True,
            add_chapters=True,
        )
        await asyncio.to_thread(pp.run, self.params | data)
        return self

    @catch
    async def embed_thumbnail(self, thumbnail: StrPath, square: bool = False) -> Self:
        pp = EmbedThumbnailPP()

        info = self.params | {
            "thumbnails": [
                {"filepath": str(thumbnail)},
            ],
        }

        if square:
            info |= {
                "postprocessor_args": {
                    "thumbnailsconvertor+ffmpeg_o": [
                        "-c:v",
                        "png",
                        "-vf",
                        "crop=ih",
                    ]
                }
            }

        await asyncio.to_thread(pp.run, info)
        return self

    @catch
    async def embed_subtitles(self, subtitles: Sequence[StrPath]) -> Self:
        pp = FFmpegEmbedSubtitlePP()

        dict_subs: dict[str, dict] = {}
        for sub in subtitles:
            path = Path(sub)

            lang = path.suffixes[0][1:]
            ext = path.suffixes[1][1:]

            dict_subs |= {
                lang: {
                    "filepath": str(path),
                    "ext": str(ext),
                },
            }

        await asyncio.to_thread(
            pp.run, self.params | {"requested_subtitles": dict_subs}
        )
        return self

    @classmethod
    @catch
    async def from_formats_merge(
        cls,
        filepath: StrPath,
        formats: RequestedFormats,
        ffmpeg_path: StrPath | None = None,
    ) -> Self:
        cls = cls(filepath, ffmpeg_path=ffmpeg_path)

        pp = FFmpegMergerPP()
        _, data = await asyncio.to_thread(
            pp.run,
            cls.params
            | {
                "requested_formats": formats,
                "__files_to_merge": [item["filepath"] for item in formats],
            },
        )
        cls._update_filepath(data)
        return cls

    @property
    def params(self):
        info = {
            "filepath": str(self.filepath),
            "ext": self.extension,
        }

        if self.ffmpeg_path:
            info |= {"ffmpeg_location": str(self.ffmpeg_path)}

        return info

    def _update_filepath(self, data: YDLExtractInfo) -> None:
        self.filepath = Path(data["filepath"])
