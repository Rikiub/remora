from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from remora._internal.processor import MediaProcessor


@pytest.fixture
def mock_processor(mocker: MockerFixture, tmp_path: Path) -> Callable:
    """Mocks FFmpeg binary, filesystem and return the media processor."""

    # Keep track of mocked modules for the current test
    patched_modules = {}

    def func(module: str) -> MediaProcessor:
        # If we already mocked this module in the current test, return the existing mock
        if module in patched_modules:
            return patched_modules[module]

        # Mock FFmpeg presence
        mocker.patch(f"{module}.get_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))

        # Mock MediaProcessor
        mock_class = mocker.patch(
            f"{module}.{MediaProcessor.__name__}",
            autospec=True,
        )

        mock_instance = mock_class.return_value
        mock_instance.file_path = tmp_path / "processed.mp4"

        # Cache it to prevent InvalidSpecError on duplicate calls
        patched_modules[module] = mock_instance

        return mock_instance

    return func
