import pytest

from remora import Client


@pytest.fixture
async def extractor() -> Client:
    return Client()
