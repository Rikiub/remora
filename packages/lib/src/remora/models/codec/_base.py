from enum import StrEnum


class Codec(StrEnum):
    @classmethod
    def __missing__(cls, value):
        """Lowercase and take everything before the first dot/dash

        Example: "avc1.640028" -> "avc1"
        Example: "mp4a.40.2"   -> "mp4a"
        """

        if not isinstance(value, str):
            return None

        value = str(value).lower().split(".")[0].split("-")[0].strip()

        for member in cls:
            if member.value.startswith(value):
                return member

        return None
