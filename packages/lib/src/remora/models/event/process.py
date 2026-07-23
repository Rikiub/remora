from typing import Annotated, Literal

from pydantic import Field

from remora.models.event._base import FileEvent
from remora.models.stream.item import AudioStream, VideoStream

ProcessorTask = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]


class Processing(FileEvent):
    status: Literal["started", "completed"]
    task: Literal[
        "change_container",
        "convert_audio",
        "embed_metadata",
        "embed_thumbnail",
        "embed_subtitles",
    ]


class MergeProcessing(Processing):
    task: Literal["merge_streams"] = "merge_streams"

    video_stream: VideoStream
    audio_stream: AudioStream


ProcessEvent = Annotated[
    Processing | MergeProcessing,
    Field(discriminator="task"),
]
