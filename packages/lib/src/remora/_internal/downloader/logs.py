from loguru import logger

from remora.models.event.enum import CompletedResult, EventStatus, EventType
from remora.models.event.media import MediaEvent
from remora.models.event.playlist import BatchEvent
from remora.models.event.process import ProcessEvent, ProcessorTask


async def log_event_playlist(event: BatchEvent):
    if event.type == EventType.PLAYLIST:
        match event.status:
            case EventStatus.STARTED:
                logger.info(
                    "Download started with {playlist_total} items",
                    playlist_total=event.total,
                )
            case EventStatus.IN_PROGRESS:
                logger.info(
                    "{playlist_completed} of {playlist_total} items completed",
                    playlist_completed=event.completed,
                    playlist_total=event.total,
                )
            case EventStatus.CANCELLED:
                logger.warning("Download cancelled")
            case EventStatus.COMPLETED:
                match event.result:
                    case CompletedResult.SUCCESS:
                        logger.success("Download completed")
                    case CompletedResult.PARTIAL:
                        logger.warning("Download completed partially")


async def log_event_media(event: MediaEvent):
    with logger.contextualize(
        media_id=event.id,
        media_title=event.media.title,
        status=event.status,
    ):
        match event.status:
            case EventStatus.PROCESSING:
                await _processor_callback(event.progress)
            case EventStatus.WARNING:
                logger.warning("Warning: {}", event.message)
            case EventStatus.FAILED:
                logger.error("Download failed: {}", event.message)
            case EventStatus.CANCELLED:
                logger.info("Download cancelled")
            case EventStatus.COMPLETED:
                log = logger.bind(
                    file_path=event.file_path,
                    file_extension=event.file_extension,
                )

                match event.result:
                    case CompletedResult.SUCCESS:
                        log.success("Completed")
                    case CompletedResult.PARTIAL:
                        log.success("Completed (Some data missed)")
                    case CompletedResult.DUPLICATE:
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
    with logger.contextualize(status=event.status, task=event.task):
        if event.status == EventStatus.COMPLETED:
            match event.task:
                case ProcessorTask.CHANGE_CONTAINER:
                    logger.debug(
                        'File container changed to "{extension}"',
                        extension=event.file_extension,
                    )
                case ProcessorTask.CONVERT_AUDIO:
                    logger.debug(
                        'File converted to "{extension}"',
                        extension=event.file_extension,
                    )
                case ProcessorTask.MERGE_STREAMS:
                    logger.debug(
                        'Merged video "{video}" and audio "{audio}" formats',
                        video=event.video_stream.extension,
                        audio=event.audio_stream.extension,
                    )
                case ProcessorTask.EMBED_SUBTITLES:
                    logger.debug("Subtitles embedded")
                case ProcessorTask.EMBED_THUMBNAIL:
                    logger.debug("Thumbnail embedded")
                case ProcessorTask.EMBED_METADATA:
                    logger.debug("Metadata embedded")
