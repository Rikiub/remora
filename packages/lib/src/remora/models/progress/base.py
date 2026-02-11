from pathlib import Path
from typing import Literal

from pydantic import BaseModel

StageType = Literal["started", "completed"]


class MediaState(BaseModel):
    type: Literal["media"] = "media"
    id: str


class HasFile(BaseModel):
    filepath: Path

    @property
    def extension(self) -> str:
        return self.filepath.suffix.lstrip(".")
