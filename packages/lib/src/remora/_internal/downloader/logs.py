from loguru import logger

from remora.models.event import (
    BatchEvent,
    MediaCancelled,
    MediaCompleted,
    MediaEvent,
    MediaFailed,
    MediaProcessing,
    MediaWarning,
    PlaylistCancelled,
    PlaylistCompleted,
    PlaylistInProgress,
    PlaylistStarted,
    Processing,
)


async def log_event_playlist(event: BatchEvent):
    match event:
        case PlaylistStarted():
            logger.info(
                "Download started with {playlist_total} items",
                playlist_total=event.total,
            )
        case PlaylistInProgress():
            logger.info(
                "{playlist_completed} of {playlist_total} items completed",
                playlist_completed=event.completed,
                playlist_total=event.total,
            )
        case PlaylistCancelled():
            logger.warning("Download cancelled")

        case PlaylistCompleted(result="success"):
            logger.success("Download completed")
        case PlaylistCompleted(result="partial"):
            logger.warning("Download completed partially")


async def log_event_media(event: MediaEvent):
    with logger.contextualize(
        media_id=event.id,
        media_title=event.media.title,
        status=event.status,
    ):
        match event:
            case MediaProcessing():
                await _processor_callback(event.progress)
            case MediaWarning():
                logger.warning("Warning: {}", event.message)
            case MediaFailed():
                logger.error("Download failed: {}", event.message)
            case MediaCancelled():
                logger.info("Download cancelled")
            case MediaCompleted():
                log = logger.bind(
                    file_path=event.file_path,
                    file_extension=event.file_extension,
                )

                match event.result:
                    case "success":
                        log.success("Completed")
                    case "partial":
                        log.success("Completed (Some data missed)")
                    case "skipped":
                        log.success(
                            'Skipped (Exists as "{file_extension}")',
                            file_extension=event.file_extension,
                            icon="🔄",
                        )

                log.debug(
                    'Final file: "{file_path}"',
                    file_path=event.file_path,
                )


async def _processor_callback(event: Processing):
    with logger.contextualize(status=event.status, task=event.task):
        if event.status == "completed":
            match event.task:
                case "change_container":
                    logger.debug(
                        'File container changed to "{extension}"',
                        extension=event.file_extension,
                    )
                case "convert_audio":
                    logger.debug(
                        'File converted to "{extension}"',
                        extension=event.file_extension,
                    )
                case "merge_streams":
                    logger.debug("Merged video and audio formats")
                case "embed_subtitles":
                    logger.debug("Subtitles embedded")
                case "embed_thumbnail":
                    logger.debug("Thumbnail embedded")
                case "embed_metadata":
                    logger.debug("Metadata embedded")
