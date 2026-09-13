from yt_dlp.networking.impersonate import ImpersonateTarget

from remora._ydl.wrapper import YDL

__all__ = ["parse_impersonate_target"]


def parse_impersonate_target(target: str) -> ImpersonateTarget:
    available_target, _ = YDL()._parse_impersonate_targets(target)

    if available_target and available_target.client:
        return available_target
    else:
        raise ValueError(f"Invalid impersonate target '{target}'")
