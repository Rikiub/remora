from typing import Literal

from remora.models.progress._base import FileState

ProcessorTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
    "merge_streams",
]


class Processing(FileState):
    status: Literal["started", "completed"]
    task: ProcessorTask
