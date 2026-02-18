from loguru import logger

from remora.models.event.media import MediaEvent, ProcessEvent


async def event_debug(event: MediaEvent):
    with logger.contextualize(
        media_id=event.id,
        media_title=event.media.title,
        status=event.status,
    ):
        match event.status:
            case "resolved":
                logger.debug("Media extraction resolved")
            case "processing":
                await _processor_callback(event)
            case "warning":
                logger.warning(event.message)
            case "finished":
                if event.result == "success":
                    logger.debug(
                        'Final file saved in: "{file}"',
                        file=event.file_path,
                    )
                elif event.result == "skipped":
                    logger.debug(
                        'File "{file}" duplicated, skipping download',
                        file=event.file_path,
                    )


async def _processor_callback(event: ProcessEvent):
    with logger.contextualize(task=event.task, step=event.step):
        if event.step == "completed":
            match event.task:
                case "change_container":
                    logger.debug(
                        'File container changed to "{extension}"',
                        extension=event.extension,
                    )
                case "convert_audio":
                    logger.debug(
                        'File converted to "{extension}"',
                        extension=event.extension,
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
