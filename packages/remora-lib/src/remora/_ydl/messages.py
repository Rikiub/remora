import re

from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import DownloadError, ExtractorError, YoutubeDLError


def sanitize_ydl_error(error: YoutubeDLError) -> str:
    """
    Extracts and sanitizes the clean error message from any yt-dlp exception.
    Strips CLI flags, bug report templates, extractor tags, and traceback noise.
    """

    # 1. Attribute Inspection Trick
    # Get original message from the exception
    if isinstance(error, ExtractorError) and getattr(error, "orig_msg", None):
        msg = str(error.orig_msg)
    elif isinstance(error, YoutubeDLError) and getattr(error, "msg", None):
        msg = str(error.msg)
    else:
        msg = str(error)

    # 2. Cut off GitHub bug report boilerplate and update prompts
    cutoffs = (
        # Cut off GitHub bug report
        "; please report this issue on https://github.com",
        ". If you believe this is an error, please report",
        "If you believe this is an error, please report",
        "Confirm you are on the latest version using",
        "please report this issue",
        # Cut off Auth and wiki links
        "Use --cookies-from-browser or --cookies",
        "See https://github.com/yt-dlp/yt-dlp/wiki",
        "for how to manually pass cookies",
    )
    for cutoff in cutoffs:
        if cutoff in msg:
            msg = msg.split(cutoff)[0]

    # 3. Regex Cleanup Pipeline
    # Remove common prefixes
    msg = re.sub(r"^(ERROR|WARNING|CRITICAL):\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"^\[[a-zA-Z0-9_-]+\]\s*([a-zA-Z0-9_-]+:\s*)?", "", msg)

    # Remove internal exception leakage (e.g., "(caused by <HTTPError 403: ...>)")
    msg = re.sub(
        r"\s*\(\s*caused by.*?\)\s*$", "", msg, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove CLI flag references
    msg = re.sub(r",?\s*stopping due to\s+--[a-z0-9_-]+", ".", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\s*\(\s*with\s+--[a-z0-9_-]+\s*\)", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\s+due to\s+--[a-z0-9_-]+", "", msg, flags=re.IGNORECASE)

    # 4. Final Formatting & Punctuation Polish
    # Remove trailing punctuation leftovers
    msg = msg.strip()
    msg = re.sub(r"[,:;/\\]+$", "", msg).strip()

    if msg:
        msg = msg[0].upper() + msg[1:]
        if not msg.endswith((".", "!", "?")):
            msg += "."

    return msg or "An unknown extraction error occurred."


def extract_status_code(
    error: ExtractorError | DownloadError,
) -> int | None:
    """
    Extracts the HTTP status code from an exception or error string.
    Checks object attributes first, falls back to regex.
    """

    if isinstance(error, ExtractorError) and isinstance(error.cause, HTTPError):
        status_code = error.cause.status
        return status_code

    if isinstance(error, DownloadError):
        if error.exc_info and error.exc_info[1]:
            original_exc = error.exc_info[1]

            if isinstance(original_exc, HTTPError):
                return original_exc.status
            elif isinstance(original_exc, ExtractorError):
                return extract_status_code(original_exc)

    else:
        return None
