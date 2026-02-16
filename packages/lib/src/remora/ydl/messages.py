from collections.abc import Callable
from typing import NamedTuple


class ExceptMsg(NamedTuple):
    matchs: list[str]
    text: str | Callable[[str], str]


MESSAGES: list[ExceptMsg] = [
    ExceptMsg(
        matchs=["HTTP Error 403"],
        text=lambda v: (
            v
            + " : You may have exceeded the page request limit, received an IP block, among others. Please try again later."
        ),
    ),
    ExceptMsg(
        matchs=["Read timed out"],
        text="Read timed out.",
    ),
    ExceptMsg(
        matchs=["Unable to download webpage"],
        text=lambda v: (
            "Invalid URL." if any(s in v for s in ("[Errno -2]", "[Errno -5]")) else v
        ),
    ),
    ExceptMsg(
        matchs=["is not a valid URL"],
        text=lambda v: v.split()[1] + " is not a valid URL.",
    ),
    ExceptMsg(
        matchs=["Unsupported URL"],
        text=lambda v: "Unsupported URL: " + v.split()[2],
    ),
    ExceptMsg(
        matchs=["Unable to extract webpage video data"],
        text="Unable to extract webpage video data.",
    ),
    ExceptMsg(
        matchs=["Private video. Sign in if you've been granted access to this video."],
        text="Private video, unable to download.",
    ),
    ExceptMsg(
        matchs=["Unable to rename file"],
        text="Unable to rename file.",
    ),
    ExceptMsg(
        matchs=["ffmpeg not found"],
        text="Postprocessing failed. FFmpeg executable not founded.",
    ),
    ExceptMsg(
        matchs=["No video formats found!"],
        text="No formats founded.",
    ),
    ExceptMsg(
        matchs=["Unable to download", "Got error"],
        text="Unable to download.",
    ),
    ExceptMsg(
        matchs=["is only available for registered users"],
        text="Only available for registered users.",
    ),
]


def format_except_message(exception: Exception) -> str:
    """Get a user friendly message of a YT-DLP message exception."""

    message: str = str(exception)

    if message.startswith("ERROR: "):
        message = message.strip("ERROR: ")

    for item in MESSAGES:
        if any(s in message for s in item.matchs):
            if callable(item.text):
                message = item.text(message)
            else:
                message = item.text
            break

    return message
