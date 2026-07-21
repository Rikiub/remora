import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent


def get_ydl_fixture(filename: str) -> dict:
    dir = ROOT_DIR / "fixtures" / "ydl"
    file = dir / filename

    if not file.is_file():
        raise FileNotFoundError(file)

    content = json.loads(file.read_bytes())
    return content
