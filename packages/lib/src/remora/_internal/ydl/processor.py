from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

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

from remora._internal.ydl.types import YDLExtractInfo
from remora.exceptions import FFmpegNotFoundError, ProcessingError
from remora.types import StrPath


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


class YDLProcessor:
    def __init__(self, file_path: StrPath, ffmpeg_path: StrPath | None = None) -> None:
        self.file_path = Path(file_path)
        self.ffmpeg_path = ffmpeg_path

        if not self.ffmpeg_path:
            raise FFmpegNotFoundError("FFmpeg is needed for use processors.")

        if not self.extension:
            raise ValueError(f'"{self.file_path}" must have a file extension')

    @property
    def extension(self) -> str:
        return self.file_path.suffix[1:]

    @catch
    def video_remuxer(self, format: str) -> Self:
        pp = FFmpegVideoRemuxerPP(
            None,
            preferedformat=format,
        )
        _, data = pp.run(self._params)
        self._update_filepath(data)
        return self

    @catch
    def extract_audio(
        self,
        format: str | None = None,
        quality: int | None = None,
    ) -> Self:
        pp = FFmpegExtractAudioPP(
            None,
            nopostoverwrites=False,
            preferredcodec=format,
            preferredquality=quality,
        )
        _, data = pp.run(self._params)
        self._update_filepath(data)
        return self

    @catch
    def embed_metadata(self, data: YDLExtractInfo):
        pp = FFmpegMetadataPP(
            None,
            add_metadata=True,
            add_chapters=True,
        )
        pp.run(self._params | data)
        return self

    @catch
    def embed_thumbnail(self, thumbnail: StrPath, square: bool = False) -> Self:
        pp = EmbedThumbnailPP()

        info = self._params | {
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

        pp.run(info)
        return self

    @catch
    def embed_subtitle(self, subtitles: Sequence[StrPath]) -> Self:
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

        pp.run(self._params | {"requested_subtitles": dict_subs})
        return self

    @catch
    def merge_formats(self, formats: list[RequestedFormat]) -> Self:
        pp = FFmpegMergerPP()
        _, data = pp.run(
            self._params
            | {
                "requested_formats": formats,
                "__files_to_merge": [item["filepath"] for item in formats],
            },
        )
        self._update_filepath(data)
        return self

    @property
    def _params(self):
        info = {
            "filepath": str(self.file_path),
            "ext": self.extension,
        }

        if self.ffmpeg_path:
            info |= {"ffmpeg_location": str(self.ffmpeg_path)}

        return info

    def _update_filepath(self, data: YDLExtractInfo) -> None:
        self.file_path = Path(data["filepath"])
