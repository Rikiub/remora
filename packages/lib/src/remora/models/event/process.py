from typing import Literal

from remora.models.event._base import FileEvent

ProcessorTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
    "merge_streams",
]


class Processing(FileEvent):
    status: Literal["started", "completed"]
    task: ProcessorTask
