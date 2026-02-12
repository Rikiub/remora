from typing import Annotated, Literal

from pydantic import Field
from remora.models.stream.types import AudioStream, VideoStream
from remora.models.progress.base import MediaState, StageType
from remora.models.progress.media import HasFile

ProcessorStateType = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]


class ProcessorState(MediaState, HasFile):
    status: Literal["processing"] = "processing"
    stage: StageType
    processor: ProcessorStateType


class MergingProcessorState(ProcessorState):
    processor: Literal["merge_formats"] = "merge_formats"  # type: ignore

    video_stream: VideoStream
    audio_stream: AudioStream


ProcessingState = Annotated[
    MergingProcessorState | ProcessorState,
    Field(discriminator="processor"),
]
