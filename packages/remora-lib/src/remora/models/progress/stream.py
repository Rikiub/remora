from pathlib import Path
from typing import Literal

from pydantic import computed_field

from remora.models.progress._base import BaseState, FileState


# Progress Types
class _BaseStream(BaseState):
    status: Literal["downloading"] = "downloading"
    speed: float = 0
    elapsed: float = 0
    downloaded_bytes: float = 0


class StreamContinuous(_BaseStream):
    total_bytes: float | None
    type: Literal["continuous"] = "continuous"

    @computed_field
    @property
    def fraction(self) -> float | None:
        if not self.total_bytes:
            return None
        return self.downloaded_bytes / self.total_bytes


class StreamSegmented(_BaseStream):
    current_segment: int = 0
    total_segments: int | None = None
    type: Literal["segmented"] = "segmented"

    @computed_field
    @property
    def fraction(self) -> float | None:
        if not self.total_segments:
            return None
        return self.current_segment / self.total_segments


# Single Stream
class StreamCompleted(FileState):
    status: Literal["completed"] = "completed"


StreamProgressState = StreamContinuous | StreamSegmented
StreamState = StreamProgressState | StreamCompleted


# Multiple streams
class BatchStreamDownloading(BaseState):
    status: Literal["downloading"] = "downloading"
    streams: list[StreamProgressState]

    @computed_field
    @property
    def downloaded_bytes(self) -> float:
        return sum(s.downloaded_bytes for s in self.streams)

    @computed_field
    @property
    def total_bytes(self) -> float | None:
        """Calculate total bytes (only if all streams provide it)"""

        total_bytes = 0

        for s in self.streams:
            t = getattr(s, "total_bytes", None)
            if t is None:
                total_bytes = None
                break
            total_bytes += t

        return total_bytes or None

    @computed_field
    @property
    def fraction(self) -> float | None:
        """Calculates the overall progress of all streams combined."""

        if not self.streams:
            return 0.0

        total_percent = 0.0
        valid_streams = 0

        for stream in self.streams:
            if f := stream.fraction:
                total_percent += f
                valid_streams += 1

        # If none of the streams have a known total, we return None (Indeterminate)
        if valid_streams == 0:
            return None

        # Average the progress of all known streams
        return total_percent / valid_streams


class BatchStreamCompleted(BaseState):
    status: Literal["completed"] = "completed"
    video_path: Path
    audio_path: Path


BatchStreamState = BatchStreamDownloading | BatchStreamCompleted
