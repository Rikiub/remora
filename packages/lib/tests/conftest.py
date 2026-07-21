import pytest
from utils import get_ydl_fixture


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_extractor(mocker):
    """Returns a factory function to mock extract_info with any JSON fixture file."""

    def _mock(filename: str):
        data = get_ydl_fixture(filename)
        return mocker.patch(
            "remora._internal.ydl.extractor.extract_info",
            return_value=data,
        )

    return _mock
