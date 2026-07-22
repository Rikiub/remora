import json
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def ydl_data():
    def _(filename: str) -> dict:
        dir = ROOT_DIR / "data" / "ydl"
        file = dir / filename

        if not file.is_file():
            raise FileNotFoundError(file)

        content = json.loads(file.read_bytes())
        return content

    return _
