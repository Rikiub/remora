from typing import Annotated, Literal

from pydantic import Field

from remora.models.event.media import FileEvent
from remora.models.stream.item import AudioStream, VideoStream

_BaseTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]
ProcessorTask = Literal[_BaseTask, "merge_formats"]


class Processing(FileEvent):
    status: Literal["started", "completed"]
    task: _BaseTask


class MergeProcessing(Processing):
    task: Literal["merge_formats"] = "merge_formats"  # type: ignore

    video_stream: VideoStream
    audio_stream: AudioStream


ProcessEvent = Annotated[
    Processing | MergeProcessing,
    Field(discriminator="task"),
]
