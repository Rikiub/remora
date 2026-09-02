import pytest

from remora import MediaExtractor


@pytest.fixture
async def extractor() -> MediaExtractor:
    return MediaExtractor()
