import pytest

from remora.extractor import MediaExtractor


@pytest.fixture
async def extractor() -> MediaExtractor:
    return MediaExtractor()
