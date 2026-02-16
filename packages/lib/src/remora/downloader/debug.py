from loguru import logger

from remora.models.event.media import MediaEvent
from remora.models.event.processor import Processing


async def event_debug(event: MediaEvent):
    match event.status:
        case "resolving":
            _log_debug(event.id, "Resolving Media")
        case "resolved":
            _log_debug(event.id, "Media resolved")
        case "processing":
            await _processor_callback(event)
        case "finished":
            _log_debug(
                event.id,
                'Final file saved as "{extension}".',
                extension=event.extension,
            )


async def _processor_callback(event: Processing):
    if event.step == "completed":
        match event.task:
            case "change_container":
                _log_debug(
                    event.id,
                    'File container changed to "{extension}".',
                    extension=event.extension,
                )
            case "convert_audio":
                _log_debug(
                    event.id,
                    'File converted to "{extension}".',
                    extension=event.extension,
                )
            case "merge_formats":
                _log_debug(
                    event.id,
                    'Merged video "{video}" and audio "{audio}" formats.',
                    video=event.video_stream.extension,
                    audio=event.audio_stream.extension,
                )
            case "embed_subtitles":
                _log_debug(
                    event.id,
                    "Subtitles embedded.",
                )
            case "embed_thumbnail":
                _log_debug(
                    event.id,
                    "Thumbnail embedded.",
                )
            case "embed_metadata":
                _log_debug(
                    event.id,
                    "Metadata embedded.",
                )


def _log_debug(id: str, log: str, **kwargs):
    text = f'"{id}": {log}'
    logger.debug(text, **kwargs)
