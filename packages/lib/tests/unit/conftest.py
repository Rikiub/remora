from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from remora.processor import MediaProcessor


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
        ffmpeg_path = Path("/usr/bin")
        mocker.patch(f"{module}.find_wheel_ffmpeg_dir", return_value=ffmpeg_path)
        mocker.patch(f"{module}.find_system_ffmpeg_dir", return_value=ffmpeg_path)

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
