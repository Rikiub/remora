from loguru import logger
from remora.models.progress.media import MediaDownloadState, ProcessingState


async def debug_callback(progress: MediaDownloadState):
    match progress.status:
        case "resolving":
            _log_debug(progress.id, "Resolving Media")
        case "resolved":
            _log_debug(progress.id, "Media resolved")
        case "processing":
            await _processor_callback(progress)
        case "completed":
            _log_debug(
                progress.id,
                'Final file saved as "{extension}".',
                extension=progress.extension,
            )


async def _processor_callback(progress: ProcessingState):
    if progress.stage == "completed":
        match progress.processor:
            case "change_container":
                _log_debug(
                    progress.id,
                    'File container changed to "{extension}".',
                    extension=progress.extension,
                )
            case "convert_audio":
                _log_debug(
                    progress.id,
                    'File converted to "{extension}".',
                    extension=progress.extension,
                )
            case "merge_formats":
                _log_debug(
                    progress.id,
                    'Merged video "{video}" and audio "{audio}" formats.',
                    video=progress.video_format.extension,
                    audio=progress.audio_format.extension,
                )
            case "embed_subtitles":
                _log_debug(
                    progress.id,
                    "Subtitles embedded.",
                )
            case "embed_thumbnail":
                _log_debug(
                    progress.id,
                    "Thumbnail embedded.",
                )
            case "embed_metadata":
                _log_debug(
                    progress.id,
                    "Metadata embedded.",
                )


def _log_debug(id: str, log: str, **kwargs):
    text = f'"{id}": {log}'
    logger.debug(text, **kwargs)
