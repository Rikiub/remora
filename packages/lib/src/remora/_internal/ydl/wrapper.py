import logging
import tempfile

from yt_dlp.YoutubeDL import YoutubeDL

from remora._internal.ydl.types import YDLParams


class YDL(YoutubeDL):
    """Custom `YoutubeDL` with suppresed output."""

    _SUPRESS_LOGGER = logging.getLogger("YoutubeDL")
    _SUPRESS_LOGGER.disabled = True

    def __init__(self, params: YDLParams | None = None, auto_init: bool = False):
        # Default parameters
        opts: YDLParams = {
            # Supress logs
            "logger": self._SUPRESS_LOGGER,
            "ignoreerrors": False,
            "consoletitle": False,
            "no_warnings": True,
            "noprogress": True,
            "quiet": True,
            # Disable Colors
            "color": {"stdout": "no_color", "stderr": "no_color"},
            # Remove FFmpeg detection for consistent results
            # If yt-dlp found a inexistent path, it'll disable FFmpeg
            "ffmpeg_location": tempfile.gettempdir(),
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(
            opts,  # type: ignore
            auto_init,
        )
