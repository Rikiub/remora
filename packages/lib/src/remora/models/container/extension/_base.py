class BaseExtension:
    @property
    def supports_thumbnails(self) -> bool:
        return False

    @property
    def supports_subtitles(self) -> bool:
        return False
