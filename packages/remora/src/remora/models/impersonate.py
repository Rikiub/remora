from typing import Literal

__all__ = [
    "ImpersonateClient",
    "validate_impersonate_target",
]
ImpersonateClient = Literal[
    "chrome",
    "edge",
    "safari",
    "firefox",
    "tor",
]


def validate_impersonate_target(target: ImpersonateClient | str) -> str:
    from remora._ydl.wrapper import parse_impersonate_target

    parsed = parse_impersonate_target(target)
    return str(parsed)
