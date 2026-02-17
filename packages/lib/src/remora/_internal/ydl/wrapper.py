import logging

from yt_dlp.YoutubeDL import YoutubeDL

from remora._internal.ydl.types import YDLParams


class YDL(YoutubeDL):
    """Custom `YoutubeDL` with suppresed output."""

    _SUPRESS_LOGGER = logging.getLogger("YoutubeDL")
    _SUPRESS_LOGGER.disabled = True

    def __init__(self, params: YDLParams | None = None, auto_init: bool = False):
        # Default parameters
        opts: YDLParams = {
            "logger": self._SUPRESS_LOGGER,
            "ignoreerrors": False,
            "consoletitle": False,
            "no_warnings": True,
            "noprogress": True,
            "quiet": True,
            "color": {"stdout": "no_color", "stderr": "no_color"},
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(
            opts,  # type: ignore
            auto_init,
        )
