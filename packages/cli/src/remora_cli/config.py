from dataclasses import dataclass

from remora.types import LOGGING_LEVELS


@dataclass(slots=True)
class _Config:
    verbose: bool = False
    quiet: bool = False
    cache: bool = False

    @property
    def log_level(self) -> LOGGING_LEVELS:
        if self.quiet:
            return "CRITICAL"
        elif self.verbose:
            return "DEBUG"
        else:
            return "INFO"


CONFIG = _Config()
