from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def root_path() -> Path:
    return Path()
