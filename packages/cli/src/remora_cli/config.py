from dataclasses import dataclass

from remora.logs import LoggingLevels


@dataclass(slots=True)
class _Config:
    verbose: bool = False
    quiet: bool = False
    cache: bool = False

    @property
    def log_level(self) -> LoggingLevels:
        if self.quiet:
            return "CRITICAL"
        elif self.verbose:
            return "DEBUG"
        else:
            return "INFO"


CONFIG = _Config()
