import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent


def get_ydl_data(filename: str) -> dict:
    dir = ROOT_DIR / "data" / "ydl"
    file = dir / filename

    if not file.is_file():
        raise FileNotFoundError(file)

    content = json.loads(file.read_bytes())
    return content
