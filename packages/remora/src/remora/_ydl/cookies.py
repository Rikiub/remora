from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.cookies import extract_cookies_from_browser as _cookies_from_browser
from yt_dlp.utils import DownloadError as YDLDownloadError

from remora._ydl.messages import sanitize_ydl_error
from remora.exceptions import DownloaderError

__all__ = ["extract_cookies_from_browser"]


def extract_cookies_from_browser(
    browser_name: str,
    profile: str = "default",
    keyring: str | None = None,
) -> YoutubeDLCookieJar:

    try:
        return _cookies_from_browser(
            browser_name,
            profile=profile,
            keyring=keyring,
        )
    except YDLDownloadError as error:
        msg = sanitize_ydl_error(error)
        raise DownloaderError(msg)
