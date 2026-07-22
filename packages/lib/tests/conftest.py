import json
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_extractor(mocker):
    """Returns a factory function to mock extract_info with any JSON fixture file."""

    def _mock(filename: str):
        data = get_ydl_data(filename)
        return mocker.patch(
            "remora._internal.ydl.extractor.extract_info",
            return_value=data,
        )

    return _mock


def get_ydl_data(filename: str) -> dict:
    dir = ROOT_DIR / "data" / "ydl"
    file = dir / filename

    if not file.is_file():
        raise FileNotFoundError(file)

    content = json.loads(file.read_bytes())
    return content
