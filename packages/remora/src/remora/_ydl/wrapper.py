import tempfile
from io import StringIO

from loguru import logger
from typing_extensions import override
from yt_dlp.networking.common import RequestDirector
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.YoutubeDL import YoutubeDL

from remora._ydl.types import YDLParams
from remora.models.options import NetworkOptions
from remora.path import get_cache_dir


class _LoguruYDLWrapper:
    """Intercepts yt-dlp logs and routes them to Loguru strictly in DEBUG mode."""

    EXCLUDED_LOGS = ("ffmpeg not found.",)

    def __init__(self) -> None:
        self.logger = logger.patch(lambda record: record.update(name="yt-dlp"))

    def debug(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.debug(msg)

    def warning(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.warning(msg)

    def error(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.error(msg)

    def exclude(self, msg: str) -> bool:
        for excluded in self.EXCLUDED_LOGS:
            if msg.startswith(excluded):
                return True
        return False


class YDL(YoutubeDL):
    """Custom `YoutubeDL` class."""

    def __init__(
        self,
        params: YDLParams | None = None,
        session: YoutubeDL | None = None,
        network_options: NetworkOptions | None = None,
        auto_init: bool = False,
    ):
        # Default parameters
        opts: YDLParams = {
            # Adapt logs
            "logger": _LoguruYDLWrapper(),
            "no_warnings": False,
            "verbose": False,
            # Remove side-effects
            "ignoreerrors": False,
            "consoletitle": False,
            "noprogress": True,
            "quiet": True,
            # Disable Colors
            "color": {"stdout": "no_color", "stderr": "no_color"},
            # Set cache dir relative to library
            "cachedir": get_cache_dir() / "ydl",
            # Remove FFmpeg detection for consistent results
            # If yt-dlp found a inexistent path, it'll disable FFmpeg
            "ffmpeg_location": tempfile.gettempdir(),
        }

        # Network parameters
        self.network_options = network_options or NetworkOptions()
        opts |= {
            "cookiefile": StringIO(cookies.to_netscape_cookies())
            if (cookies := self.network_options.cookies)
            else None,
            "proxy": str(proxy) if (proxy := self.network_options.proxy) else None,
            "impersonate": ImpersonateTarget.from_str(impersonate)
            if (impersonate := self.network_options.impersonate)
            else None,
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(
            opts,  # type: ignore
            auto_init,
        )

        # Set shared request session
        self._shared_request_director = None

        if session:
            self._shared_request_director = session._request_director

    @override
    def build_request_director(self, handlers, preferences=None) -> RequestDirector:
        if self._shared_request_director:
            return self._shared_request_director
        else:
            return super().build_request_director(handlers, preferences)


def parse_impersonate_target(target: str) -> ImpersonateTarget:
    available_target, _ = YDL()._parse_impersonate_targets(target)

    if available_target and available_target.client:
        return available_target
    else:
        raise ValueError(f"Invalid impersonate target '{target}'")
