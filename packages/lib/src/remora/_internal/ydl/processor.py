from collections.abc import Sequence
from pathlib import Path
from typing import Self, TypedDict

from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP
from yt_dlp.postprocessor.ffmpeg import (
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegFixupM4aPP,
    FFmpegMergerPP,
    FFmpegMetadataPP,
    FFmpegPostProcessorError,
    FFmpegVideoRemuxerPP,
)

from remora._internal.ydl.messages import sanitize_ydl_error
from remora._internal.ydl.types import YDLExtractInfo
from remora._internal.ydl.wrapper import YDL
from remora.exceptions import ProcessorError
from remora.ffmpeg import validate_ffmpeg_dir
from remora.models.types import StrPath


def catch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FFmpegPostProcessorError as error:
            error = sanitize_ydl_error(error)
            raise ProcessorError(str(error))

    return wrapper


class RequestedFormat(TypedDict):
    filepath: str
    vcodec: str
    acodec: str


class YDLProcessor:
    def __init__(self, file_path: StrPath, ffmpeg_dir: StrPath | None = None) -> None:
        self.file_path = Path(file_path)
        self.ffmpeg_dir = validate_ffmpeg_dir(ffmpeg_dir)

        if not self.file_extension:
            raise ValueError(f'"{self.file_path}" must have a file extension')

    @property
    def file_extension(self) -> str:
        return self.file_path.suffix[1:]

    @catch
    def video_remuxer(self, format: str) -> Self:
        pp = FFmpegVideoRemuxerPP(
            self._ydl(),
            preferedformat=format,
        )
        _, data = pp.run(self._pp_params)
        self._update_filepath(data)
        return self

    @catch
    def extract_audio(
        self,
        format: str | None = None,
        quality: int | None = None,
    ) -> Self:
        pp = FFmpegExtractAudioPP(
            self._ydl(),
            nopostoverwrites=False,
            preferredcodec=format,
            preferredquality=quality,
        )
        _, data = pp.run(self._pp_params)
        self._update_filepath(data)
        return self

    @catch
    def embed_metadata(self, data: YDLExtractInfo) -> Self:
        pp = FFmpegMetadataPP(
            self._ydl(),
            add_metadata=True,
            add_chapters=True,
        )
        pp.run(self._pp_params | data)
        return self

    @catch
    def embed_thumbnail(self, thumbnail: StrPath, square: bool = False) -> Self:
        pp = EmbedThumbnailPP(self._ydl())
        info = self._pp_params | {
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
        pp = FFmpegEmbedSubtitlePP(self._ydl())

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

        pp.run(self._pp_params | {"requested_subtitles": dict_subs})
        return self

    @catch
    def merge_formats(
        self,
        merge_format: str,
        formats: list[RequestedFormat],
    ) -> Self:
        pp = FFmpegMergerPP(
            self._ydl(
                {"merge_output_format": merge_format},
            )
        )

        _, data = pp.run(
            self._pp_params
            | {
                "requested_formats": formats,
                "__files_to_merge": [f["filepath"] for f in formats],
            },
        )
        self._update_filepath(data)
        return self

    @catch
    def fix_m4a(self) -> Self:
        if self.file_extension == "m4a":
            pp_fix = FFmpegFixupM4aPP(self._ydl())
            _, data = pp_fix.run(self._pp_params | {"container": "m4a_dash"})
            self._update_filepath(data)
        return self

    def _ydl(self, params: dict | None = None) -> YDL:
        params = params or {}
        params |= {"ffmpeg_location": str(self.ffmpeg_dir)}
        return YDL(params)

    @property
    def _pp_params(self):
        info = {
            "filepath": str(self.file_path),
            "ext": self.file_extension,
        }
        return info

    def _update_filepath(self, data: YDLExtractInfo) -> None:
        self.file_path = Path(data["filepath"])
