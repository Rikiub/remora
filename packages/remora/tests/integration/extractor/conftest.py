import pytest

from remora import MediaExtractor
from remora.session import Session


@pytest.fixture
async def extractor() -> MediaExtractor:
    return MediaExtractor(Session.create())
