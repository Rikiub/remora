from loguru import logger

from remora.models.event.media import MediaEvent, ProcessEvent
from remora.models.event.playlist import BatchEvent


async def log_event_playlist(event: BatchEvent):
    if event.type == "playlist":
        match event.status:
            case "started":
                logger.info(
                    "Download started with {playlist_total} items",
                    playlist_total=event.total,
                )
            case "in_progress":
                logger.info(
                    "{playlist_completed} of {playlist_total} items completed",
                    playlist_completed=event.completed,
                    playlist_total=event.total,
                )
            case "cancelled":
                logger.warning("Download cancelled")
            case "completed":
                match event.result:
                    case "success":
                        logger.success("Download completed")
                    case "partial":
                        logger.warning("Download completed partially")


async def log_event_media(event: MediaEvent):
    with logger.contextualize(
        media_id=event.id,
        media_title=event.media.title,
        status=event.status,
    ):
        match event.status:
            case "processing":
                await _processor_callback(event)
            case "warning":
                logger.warning("Warning: {}", event.message)
            case "failed":
                logger.error("Download failed: {}", event.message)
            case "cancelled":
                logger.info("Download cancelled")
            case "completed":
                log = logger.bind(
                    file_path=event.file_path,
                    file_extension=event.file_extension,
                )

                match event.result:
                    case "success":
                        log.success("Completed")
                    case "partial":
                        log.success("Completed (Some data missed)")
                    case "duplicate":
                        log.success(
                            'Skipped (Exists as "{file_extension}")',
                            file_extension=event.file_extension,
                            icon="🔄",
                        )

                log.debug(
                    'Final file: "{file_path}"',
                    file_path=event.file_path,
                )


async def _processor_callback(event: ProcessEvent):
    with logger.contextualize(task=event.task, step=event.step):
        if event.step == "completed":
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
                case "merge_formats":
                    logger.debug(
                        'Merged video "{video}" and audio "{audio}" formats',
                        video=event.video_stream.extension,
                        audio=event.audio_stream.extension,
                    )
                case "embed_subtitles":
                    logger.debug("Subtitles embedded")
                case "embed_thumbnail":
                    logger.debug("Thumbnail embedded")
                case "embed_metadata":
                    logger.debug("Metadata embedded")
