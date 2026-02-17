import hashlib
import time

from anyio import Path

from remora._internal.path import get_cache_dir
from remora.types import StrUrl

EXPIRATION = 24 * 60 * 60


async def load_info(url: StrUrl) -> str | None:
    dir = Path(get_cache_dir())
    file = dir / _url_hash(url)

    if await file.exists():
        stats = await file.stat()
        age = time.time() - stats.st_mtime

        if age < EXPIRATION:
            return await file.read_text()

    return None


async def save_info(url: str, content: str):
    dir = Path(get_cache_dir())
    file = dir / _url_hash(url)
    await file.write_text(content)


async def remove_info(url: str) -> bool:
    dir = Path(get_cache_dir())
    file = dir / _url_hash(url)

    if await file.exists():
        await file.unlink()
        return True
    return False


def _url_hash(url: StrUrl) -> str:
    hash = hashlib.sha256(str(url).encode()).hexdigest()
    return f"{hash}.json"
