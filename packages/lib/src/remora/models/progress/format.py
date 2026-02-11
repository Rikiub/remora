from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from remora.models.progress.base import HasFile
from typing_extensions import Self


class DownloadingFormatState(BaseModel):
    status: Literal["downloading"] = "downloading"

    downloaded_bytes: float = 0
    total_bytes: float = 0

    speed: float = 0
    elapsed: float = 0

    def _ydl_progress(self, data: dict, callback: Callable[[Self], None]) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        d = data

        match d["status"]:
            case "downloading":
                downloaded_bytes = d.get("downloaded_bytes") or 0
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

                if downloaded_bytes > self.downloaded_bytes:
                    self.downloaded_bytes = downloaded_bytes

                if total_bytes > self.total_bytes:
                    self.total_bytes = total_bytes

                self.speed = d.get("speed") or 0
                self.elapsed = d.get("elapsed") or 0
            case "finished":
                self.downloaded_bytes = self.total_bytes

        callback(self)


class CompletedFormatState(HasFile):
    status: Literal["completed"] = "completed"


FormatState = Annotated[
    DownloadingFormatState | CompletedFormatState,
    Field(discriminator="status"),
]
