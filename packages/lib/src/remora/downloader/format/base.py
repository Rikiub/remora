from abc import ABC, abstractmethod
from anyio import Path
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback, FormatState
from remora.types import StrPath

DEFAULT_RETRIES = 3


class BaseFormatDownloader(ABC):
    SUPPORTED_PROTOCOLS: list[str]

    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        on_progress: FormatDownloadCallback | None = None,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.filepath = Path(filepath)
        self.format = format
        self.format_state = FormatState()
        self.progress = on_progress
        self.retries = retries

    @abstractmethod
    async def download(self) -> Path: ...
