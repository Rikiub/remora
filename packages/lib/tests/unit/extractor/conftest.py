import pytest
from pytest_mock import MockerFixture

from remora._internal.extractor import MediaExtractor


@pytest.fixture
async def extract_ydl(mock_extractor):
    async def _(filename: str):
        mock_extractor(filename)
        return await MediaExtractor().extract("")

    return _


@pytest.fixture
def mock_extractor(mocker: MockerFixture, ydl_data):
    """Returns a factory function to mock extract_info with any JSON fixture file."""

    def _mock(filename: str):
        data = ydl_data(filename)
        return mocker.patch(
            "remora._internal.ydl.wrapper.YDL.extract_info",
            return_value=data,
        )

    return _mock
