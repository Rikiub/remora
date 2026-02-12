from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field
from remora.models.progress.base import HasFile, MediaState
from remora.models.content.media import LazyMedia, Media
from remora.models.progress.stream import DownloadingStreamState
from remora.models.progress.processor import ProcessingState


class ResolvingState(MediaState):
    status: Literal["resolving"] = "resolving"
    media: LazyMedia


class ResolvedState(MediaState):
    status: Literal["resolved"] = "resolved"
    media: Media


class RetryingState(MediaState):
    status: Literal["retrying"] = "retrying"
    reason: Literal["stale_cache"]


class DownloadingState(DownloadingStreamState, MediaState): ...


class WarningState(MediaState):
    status: Literal["warning"] = "warning"
    message: str


class CompletedState(MediaState, HasFile):
    status: Literal["completed"] = "completed"
    reason: Literal["success", "incomplete", "skipped", "failed"]


MediaDownloadState = Annotated[
    ResolvingState
    | ResolvedState
    | DownloadingState
    | RetryingState
    | ProcessingState
    | WarningState
    | CompletedState,
    Field(discriminator="status"),
]
