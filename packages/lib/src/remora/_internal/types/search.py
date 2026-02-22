from enum import StrEnum
from typing import Literal


class SearchService(StrEnum):
    SOUNDCLOUD = "soundcloud"
    YOUTUBE = "youtube"
    YTMUSIC = "ytmusic"


SearchServiceStr = Literal[
    "soundcloud",
    "youtube",
    "ytmusic",
]
SearchServiceLike = SearchService | SearchServiceStr
