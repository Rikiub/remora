import json
from pathlib import Path
from typing import Literal

from rich import print, traceback

from remora.models.media.item import Media

traceback.install()

dir = Path(__file__).parent
mode: Literal["media", "playlist"] = "media"

match mode:
    case "media":
        info = dir / "video.json"
        info = json.loads(info.read_bytes())
        data = Media(**info)
        print(data)
    case "playlist":
        info = dir / "playlist.json"
        info = json.loads(info.read_bytes())
        data = YDLInfoParser.playlist(info)
        print(data)
