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
            case "update":
                logger.info(
                    "{playlist_completed} of {playlist_total} items completed",
                    playlist_completed=event.completed,
                    playlist_total=event.total,
                )
            case "finished":
                match event.result:
                    case "success":
                        logger.success("Download completed")
                    case "incomplete":
                        logger.warning("Download completed with errors")
                    case "cancelled":
                        logger.warning("Download cancelled")


async def log_event_media(event: MediaEvent):
    with logger.contextualize(
        media_id=event.id,
        media_title=event.media.title,
        status=event.status,
    ):
        match event.status:
            case "resolved":
                logger.info("Media extraction resolved")
            case "processing":
                await _processor_callback(event)
            case "warning":
                logger.warning(event.message)
            case "finished":
                log = logger.bind(
                    file_path=event.file_path,
                    file_extension=event.file_extension,
                )

                match event.result:
                    case "success":
                        log.success("Completed")
                    case "incomplete":
                        log.success("Completed with errors")
                    case "skipped":
                        log.success(
                            'Skipped (Exists as "{file_extension}")',
                            file_extension=event.file_extension,
                            icon="🔄",
                        )
                    case "failed":
                        log.error("Download failed")

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
