import json
from pathlib import Path
from typing import Literal

from rich import print, traceback

from remora.models.media.item import Media
from remora.models.media.list import Playlist

traceback.install()

dir = Path(__file__).parent
mode: Literal["media", "playlist"] = "playlist"

match mode:
    case "media":
        info = dir / "video.json"
        info = json.loads(info.read_bytes())
        data = Media(**info)
        print(data.to_ydl_dict())
    case "playlist":
        info = dir / "playlist.json"
        info = json.loads(info.read_bytes())
        data = Playlist(**info)
        print(data)
