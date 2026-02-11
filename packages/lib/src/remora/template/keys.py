"""Read pre-serialized keys from JSON to improve startup time on shell autocomplete."""


def get_keys() -> list[str]:
    import json
    from pathlib import Path

    keys: list[str]

    filepath = Path(__file__)
    filepath = filepath.parent / f"{filepath.stem}.json"

    if filepath.is_file():
        with filepath.open() as f:
            keys = json.load(f)
    else:
        keys = list(_generate_keys())
        filepath.write_text(json.dumps(keys))

    return keys


def _generate_keys() -> set[str]:
    """Should be executed only one time."""

    from pydantic import BaseModel
    from remora.models.content.list import Playlist
    from remora.models.content.media import Media
    from remora.models.format.types import AudioFormat, Format, VideoFormat, YDLArgs

    def extract(model: type[BaseModel], by_alias: bool = False) -> list[str]:
        keys: list[str] = []

        for name, info in model.model_fields.items():
            if by_alias and info.alias:
                keys.append(info.alias)
            else:
                keys.append(name)

        return keys

    EXCLUDED_KEYS = {
        *extract(YDLArgs),
        "extractor_key",
        "_type",
        "type",
        "medias",
        "playlists",
        "formats",
        "subtitles",
        "chapters",
        "thumbnails",
        "datetime",
        "extension",
    }
    templates = {
        *extract(Playlist, True),
        *extract(Media),
        *extract(Format),
        *extract(VideoFormat),
        *extract(AudioFormat),
    }

    for key in EXCLUDED_KEYS:
        templates.discard(key)

    return templates
