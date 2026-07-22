import pytest

from remora._internal.extractor import MediaExtractor


@pytest.fixture
async def extractor() -> MediaExtractor:
    return MediaExtractor()
