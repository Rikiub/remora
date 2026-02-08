from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field, RootModel

from remora.models.content.base import YDLSerializable
from remora.types import StrPath


def _validate_artists(value: list[str]) -> list[str]:
    if value and len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class MusicMetadata(YDLSerializable):
    track: str = ""
    artists: Annotated[list[str] | None, BeforeValidator(_validate_artists)] = None
    album: str = ""
    album_artist: str = ""
    genres: list[str] | None = None


class Chapter(YDLSerializable):
    start_time: int
    end_time: int
    title: str


class Subtitle(YDLSerializable):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


class Thumbnail(YDLSerializable):
    id: str = ""
    url: str
    width: int = 0
    height: int = 0

    def download(self, filepath: StrPath) -> Path:
        from remora.downloader.metadata import download_thumbnail

        return download_thumbnail(filepath, self)


class Subtitles(YDLSerializable, RootModel[dict[str, list[Subtitle]]]):
    def download(self, filepath: StrPath) -> list[Path]:
        from remora.downloader.metadata import download_subtitles

        return download_subtitles(filepath, self)

    def __getitem__(self, index: int | str) -> list[Subtitle]:
        match index:
            case int():
                return list(self.root.values())[index]  # type: ignore
            case str():
                return self.root[index]
            case _:
                raise TypeError(index)

    def __bool__(self) -> bool:
        return bool(self.root)
