from loguru import logger

from remora.models.progress import (
    BatchState,
    MediaCancelled,
    MediaCompleted,
    MediaFailed,
    MediaProcessing,
    MediaSkipped,
    MediaState,
    MediaWarning,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
    Processing,
)


async def log_event_playlist(state: BatchState):
    match state:
        case PlaylistStarted():
            logger.info(
                "Download started with {playlist_total} items",
                playlist_total=state.total,
            )
        case PlaylistInProgress():
            logger.info(
                "{playlist_completed} of {playlist_total} items completed",
                playlist_completed=state.completed,
                playlist_total=state.total,
            )
        case PlaylistCancelled():
            logger.warning("Download cancelled")

        case PlaylistCompleted(result="success"):
            logger.success("Download completed")
        case PlaylistCompleted(result="partial"):
            logger.warning("Download completed partially")


async def log_event_media(state: MediaState):
    with logger.contextualize(
        media_id=state.id,
        media_title=state.media.title,
        status=state.status,
    ):
        match state:
            case MediaProcessing():
                await _processor_callback(state.progress)
            case MediaWarning():
                logger.warning("Warning: {}", state.message)
            case MediaFailed():
                logger.error("Download failed: {}", state.message)
            case MediaCancelled():
                logger.info("Download cancelled")
            case MediaSkipped():
                logger.success(
                    'Skipped (Exists as "{file_extension}")',
                    file_path=state.file_path,
                    file_extension=state.file_extension,
                )
            case MediaCompleted(result="success"):
                logger.success(
                    "Completed",
                    file_path=state.file_path,
                    file_extension=state.file_extension,
                )
            case MediaCompleted(result="partial"):
                logger.success(
                    "Completed (Some data missed)",
                    file_path=state.file_path,
                    file_extension=state.file_extension,
                )


async def _processor_callback(state: Processing):
    with logger.contextualize(status=state.status, task=state.task):
        if state.status == "completed":
            match state.task:
                case "change_container":
                    logger.debug(
                        'File container changed to "{extension}"',
                        extension=state.file_extension,
                    )
                case "convert_audio":
                    logger.debug(
                        'File converted to "{extension}"',
                        extension=state.file_extension,
                    )
                case "merge_streams":
                    logger.debug("Merged video and audio formats")
                case "embed_subtitles":
                    logger.debug("Subtitles embedded")
                case "embed_thumbnail":
                    logger.debug("Thumbnail embedded")
                case "embed_metadata":
                    logger.debug("Metadata embedded")
