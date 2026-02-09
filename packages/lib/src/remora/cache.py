import hashlib
import time

from remora.path import CACHE_DIR
from remora.types import StrUrl

EXPIRATION = 24 * 60 * 60


def load_info(url: StrUrl) -> str | None:
    file = CACHE_DIR / _url_hash(url)

    if file.exists():
        age = time.time() - file.stat().st_mtime
        if age < EXPIRATION:
            return file.read_text()

    return None


def save_info(url: str, content: str):
    file = CACHE_DIR / _url_hash(url)
    file.write_text(content)


def remove_info(url: str) -> bool:
    file = CACHE_DIR / _url_hash(url)

    if file.exists():
        file.unlink()
        return True
    return False


def _url_hash(url: StrUrl) -> str:
    hash = hashlib.sha256(str(url).encode()).hexdigest()
    return f"{hash}.json"
