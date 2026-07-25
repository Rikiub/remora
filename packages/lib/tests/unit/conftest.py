from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from remora._internal.processor import MediaProcessor


@pytest.fixture
def mocker_processor(mocker: MockerFixture, tmp_path: Path) -> Callable:
    """Mocks FFmpeg binary, filesystem and return the media processor."""

    def func(module: str) -> MediaProcessor:
        # Mock FFmpeg presence
        mocker.patch(f"{module}.get_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))

        # Mock MediaProcessor (FFmpeg bindings)
        mock_processor: MediaProcessor = mocker.patch(
            f"{module}.MediaProcessor"
        ).return_value
        mock_processor.file_path = tmp_path / "processed.mp4"

        # Mock its async methods
        mock_processor.merge_streams = AsyncMock(return_value=mock_processor)
        mock_processor.change_container = AsyncMock()
        mock_processor.embed_subtitles = AsyncMock()
        mock_processor.embed_metadata = AsyncMock()
        mock_processor.embed_thumbnail = AsyncMock()

        return mock_processor

    return func
