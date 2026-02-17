from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import BaseMediaEvent
from remora.models.event.media import FileEvent
from remora.models.stream.format import AudioStream, VideoStream

ProcessorTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]


class Processing(BaseMediaEvent, FileEvent):
    status: Literal["processing"] = "processing"
    step: Literal["started", "completed"]
    task: ProcessorTask


class MergeProcessing(Processing):
    task: Literal["merge_formats"] = "merge_formats"  # type: ignore

    video_stream: VideoStream
    audio_stream: AudioStream


ProcessEvent = Annotated[
    Processing | MergeProcessing,
    Field(discriminator="task"),
]
