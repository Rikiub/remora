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

from remora.exceptions import FFmpegNotFoundError, ProcessingError
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


class YDLProcessor:
    def __init__(self, filepath: StrPath, ffmpeg_path: StrPath | None = None) -> None:
        self.filepath = Path(filepath)
        self.ffmpeg_path = ffmpeg_path

        if not self.ffmpeg_path:
            raise FFmpegNotFoundError("FFmpeg is needed for use processors.")

        if not self.extension:
            raise ValueError(f'"{self.filepath}" must have a file extension')

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]

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

    @classmethod
    @catch
    def from_merger(
        cls,
        filepath: StrPath,
        formats: list[RequestedFormat],
        ffmpeg_path: StrPath | None = None,
    ) -> Self:
        cls = cls(filepath, ffmpeg_path=ffmpeg_path)

        pp = FFmpegMergerPP()
        _, data = pp.run(
            cls._params
            | {
                "requested_formats": formats,
                "__files_to_merge": [item["filepath"] for item in formats],
            },
        )
        cls._update_filepath(data)
        return cls

    @property
    def _params(self):
        info = {
            "filepath": str(self.filepath),
            "ext": self.extension,
        }

        if self.ffmpeg_path:
            info |= {"ffmpeg_location": str(self.ffmpeg_path)}

        return info

    def _update_filepath(self, data: YDLExtractInfo) -> None:
        self.filepath = Path(data["filepath"])
