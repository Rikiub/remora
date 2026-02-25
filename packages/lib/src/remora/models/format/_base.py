from remora.models.format.type import FormatKind


class BaseExtension:
    @classmethod
    def get_safe_extensions(cls):
        return [e.value for e in cls if e.is_safe]  # type: ignore

    @property
    def is_safe(self) -> bool:
        return False

    @property
    def is_common(self) -> bool:
        return False

    @property
    def type(self) -> FormatKind:
        raise NotImplementedError()

    @property
    def supports_thumbnails(self) -> bool:
        return False

    @property
    def supports_subtitles(self) -> bool:
        return False
