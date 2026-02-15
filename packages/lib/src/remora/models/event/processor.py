from typing import Annotated, Literal

from pydantic import Field
from remora.models.event.base import BaseMediaEvent
from remora.models.event.media import FileEvent
from remora.models.stream.types import AudioStream, VideoStream

ProcessorTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]


class Processor(BaseMediaEvent, FileEvent):
    status: Literal["processing"] = "processing"
    step: Literal["started", "completed"]
    task: ProcessorTask


class MergingProcessor(Processor):
    task: Literal["merge_formats"] = "merge_formats"  # type: ignore

    video_stream: VideoStream
    audio_stream: AudioStream


Processing = Annotated[
    Processor | MergingProcessor,
    Field(discriminator="task"),
]
