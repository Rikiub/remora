from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Awaitable, Literal

from pydantic import Field

from remora.models.content.media import LazyMedia, Media
from remora.models.progress.base import HasFile, State
from remora.models.progress.format import FormatState
from remora.models.progress.processor import ProcessingState


class ResolvingState(State):
    status: Literal["resolving"] = "resolving"
    media: LazyMedia


class ResolvedState(State):
    status: Literal["resolved"] = "resolved"
    media: Media


class RetryingState(State):
    status: Literal["retrying"] = "retrying"
    reason: Literal["stale_cache"]


class DownloadingState(FormatState, State):
    status: Literal["downloading"] = "downloading"


class WarningState(State):
    status: Literal["warning"] = "warning"
    message: str


class CompletedState(HasFile):
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


MediaDownloadCallback = Callable[[MediaDownloadState], Awaitable[None]]
