from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from remora.models.event.enum import EventStatus
from remora.models.event.media import FileEvent
from remora.models.stream.item import AudioStream, VideoStream


class ProcessorTask(StrEnum):
    CHANGE_CONTAINER = "change_container"
    CONVERT_AUDIO = "convert_audio"
    EMBED_METADATA = "embed_metadata"
    EMBED_THUMBNAIL = "embed_thumbnail"
    EMBED_SUBTITLES = "embed_subtitles"
    MERGE_STREAMS = "merge_streams"


class Processing(FileEvent):
    status: Literal[EventStatus.STARTED, EventStatus.COMPLETED]
    task: Literal[
        ProcessorTask.CHANGE_CONTAINER,
        ProcessorTask.CONVERT_AUDIO,
        ProcessorTask.EMBED_METADATA,
        ProcessorTask.EMBED_THUMBNAIL,
        ProcessorTask.EMBED_SUBTITLES,
        "change_container",
        "convert_audio",
        "embed_metadata",
        "embed_thumbnail",
        "embed_subtitles",
    ]


class MergeProcessing(Processing):
    task: Literal[ProcessorTask.MERGE_STREAMS, "merge_streams"] = (  # type: ignore
        ProcessorTask.MERGE_STREAMS
    )

    video_stream: VideoStream
    audio_stream: AudioStream


ProcessEvent = Annotated[
    Processing | MergeProcessing,
    Field(discriminator="task"),
]
