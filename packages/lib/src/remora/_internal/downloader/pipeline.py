import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import anyio
from anyio.to_thread import run_sync
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.event_streamer import AsyncEventStreamer
from remora._internal.downloader.logs import log_event_media
from remora._internal.downloader.metadata import download_subtitles, download_thumbnail
from remora._internal.downloader.selector import StreamSelector
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.downloader.stream.muxed import MuxedStreamDownloader
from remora._internal.extractor import MediaExtractor
from remora._internal.ffmpeg import find_internal_ffmpeg, find_system_ffmpeg
from remora._internal.path import get_tempfile
from remora._internal.processor import MediaProcessor
from remora._internal.template.output import format_template
from remora._internal.types import StreamContext
from remora.exceptions import (
    DownloaderError,
    ExtractorError,
    MetadataDownloaderError,
    ProcessorError,
)
from remora.models.container import (
    AVContainer,
)
from remora.models.download_options import DownloadOptions
from remora.models.event import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    MediaCancelled,
    MediaCompleted,
    MediaDownloading,
    MediaEvent,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaWarning,
    Processing,
    ProcessorTask,
    StreamProgressEvent,
)
from remora.models.media import LazyMedia, Media
from remora.models.stream import AudioStream, Stream, VideoStream
from remora.types import StrPath


@dataclass(slots=True)
class DownloadContext:
    video: StreamContext[VideoStream] | None = None
    audio: StreamContext[AudioStream] | None = None
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class DownloadPipeline(AsyncEventStreamer[MediaEvent]):
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.id = media.id
        self.media: Media = media  # ty: ignore[invalid-assignment]
        self.config = config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()
        self.has_missing_data = False
        self.ffmpeg_path = self._get_ffmpeg_binary()

        super().__init__(buffer_size=30)

    @override
    async def _emit(self, event) -> None:
        """Safely dispatches and logs pipeline events."""
        await log_event_media(event)
        await super()._emit(event)

    @override
    async def _on_cancelled(self) -> None:
        await self._emit(MediaCancelled(id=self.id, media=self.media))

    @override
    async def _run_pipeline(self):
        media = await self._resolve_media()

        with logger.contextualize(media_id=self.id, media_title=media.title):
            try:
                await self._pipeline(media)
            except (DownloaderError, ExtractorError, ProcessorError) as error:
                logger.error(str(error))
                raise

    async def _pipeline(self, media: Media):
        """The one who orchestrate the jobs."""

        # Select Best Streams
        selected = StreamSelector(
            self.config,
            merge_available=bool(self.ffmpeg_path),
        ).resolve(media)

        metadata_stream = selected.muxed or selected.video or selected.audio
        if not metadata_stream:
            error = "Streams not found"
            await self._emit(
                MediaFailed(
                    id=self.id,
                    media=self.media,
                    message=error,
                )
            )
            raise DownloaderError(error)

        # Calculate Path & Check Existence
        output = format_template(
            self.config.output_template,
            stream=metadata_stream,
            media=media,
            default_missing="NA",
        )
        output = anyio.Path(output)
        await output.parent.mkdir(parents=True, exist_ok=True)

        # Skip if option is enabled and a duplicate is found
        if self.config.skip_existing and await self._check_output_duplicate(output):
            return

        # Download resources like streams, subtitles and thumbnail
        with logger.contextualize(status="downloading"):
            results = await self._download_resources(
                media,
                selected.muxed or selected.video,
                selected.audio,
            )

        # Determine stable file
        if self.ffmpeg_path and (results.video and results.audio):
            file_path = await self._process_merge(
                video=results.video,
                audio=results.audio,
            )
        elif results.video:
            file_path = results.video.path
        elif results.audio:
            file_path = results.audio.path
        else:
            raise ValueError("Neither video or audio was downloaded")

        # Post-process file
        if self.ffmpeg_path:
            with logger.contextualize(status="processing"):
                file_path = await self._post_process(
                    file_path,
                    metadata_stream,
                    results.thumbnail,
                    results.subtitles,
                )
        else:
            await self._emit(
                MediaWarning(
                    id=self.id,
                    media=self.media,
                    message="FFmpeg unavailable, skipping post-processing",
                )
            )

        # Complete (Move file to target)
        await self._move_to_final(file_path, output)

    async def _resolve_media(self) -> Media:
        await self._emit(MediaExtracting(id=self.id, media=self.media))
        media = cast(LazyMedia | Media, self.media)

        if not isinstance(media, Media):
            try:
                self.media = await self.extractor.extract(media)
            except ExtractorError as error:
                await self._emit(
                    MediaFailed(
                        id=self.id,
                        media=self.media,
                        message=str(error),
                    )
                )
                raise

        return self.media

    async def _check_output_duplicate(self, output: StrPath) -> Path | None:
        output = anyio.Path(output)

        async for path in output.parent.iterdir():
            if (
                await path.is_file()
                and path.stem == output.name
                and AVContainer.get(path.suffix.lstrip("."))
            ):
                path = Path(path)
                await self._emit(
                    MediaCompleted(
                        id=self.id,
                        media=self.media,
                        file_path=path,
                        result="skipped",
                    )
                )
                return path

    async def _download_resources(
        self,
        media: Media,
        video_stream: VideoStream | None,
        audio_stream: AudioStream | None,
    ) -> DownloadContext:
        context = DownloadContext()

        async def format():
            if not (video_stream or audio_stream):
                raise ValueError("At least one stream type must be provided")

            # Get situable downloader
            if video_stream and audio_stream:
                downloader = MuxedStreamDownloader(
                    video=StreamContext(
                        stream=video_stream,
                        path=get_tempfile(),
                    ),
                    audio=StreamContext(
                        stream=audio_stream,
                        path=get_tempfile(),
                    ),
                )
            else:
                downloader = StreamDownloader(
                    output_path=get_tempfile(),
                    stream=video_stream or audio_stream,  # ty: ignore[invalid-argument-type]
                )

            try:
                async with downloader.start() as progress:
                    async for event in progress:
                        if event.status == "downloading":
                            # Normalize single downloads
                            if isinstance(event, StreamProgressEvent):
                                event = BatchStreamDownloading(streams=[event])

                            await self._emit(
                                MediaDownloading(
                                    id=self.id,
                                    media=self.media,
                                    progress=event,
                                )
                            )
                        elif event.status == "completed":
                            if video_stream:
                                context.video = StreamContext(
                                    stream=video_stream,
                                    path=event.video_path
                                    if isinstance(event, BatchStreamCompleted)
                                    else event.file_path,
                                )
                            elif audio_stream:
                                context.audio = StreamContext(
                                    stream=audio_stream,
                                    path=event.audio_path
                                    if isinstance(event, BatchStreamCompleted)
                                    else event.file_path,
                                )

                if context.video:
                    logger.debug(
                        'Video stream downloaded: "{path}"',
                        path=context.video.path,
                    )
                elif context.audio:
                    logger.debug(
                        'Audio stream downloaded: "{path}"',
                        path=context.audio.path,
                    )
            except DownloaderError as error:
                await self._emit(
                    MediaFailed(
                        id=self.id,
                        media=self.media,
                        message=str(error),
                    )
                )
                raise

        async def thumbnail():
            if media.thumbnails:
                try:
                    logger.debug("Downloading thumbnail")
                    context.thumbnail = await download_thumbnail(
                        media.thumbnails[0],
                        get_tempfile(),
                    )
                    logger.debug("Thumbnail downloaded")
                except MetadataDownloaderError as error:
                    await self._emit(
                        MediaWarning(
                            id=self.id,
                            media=self.media,
                            message=str(error),
                        )
                    )

        async def subtitles():
            if media.subtitles:
                try:
                    logger.debug("Downloading subtitles")
                    context.subtitles = await download_subtitles(
                        media.subtitles,
                        get_tempfile(),
                    )
                    logger.debug("Subtitles downloaded")
                except MetadataDownloaderError as error:
                    await self._emit(
                        MediaWarning(
                            id=self.id,
                            media=self.media,
                            message=str(error),
                        )
                    )

        async with anyio.create_task_group() as tg:
            tg.start_soon(format)
            tg.start_soon(thumbnail)
            tg.start_soon(subtitles)

        return context

    async def _process_merge(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
    ) -> Path:
        # Get container and extension
        convert = AVContainer.get(self.config.convert_to)

        if convert and not convert.is_audio_only:
            container = convert
        else:
            container = AVContainer.MP4

        extension = container.get_extension()

        # Setup events
        file_path = Path(f"{get_tempfile()}.{extension}")
        merging = MediaProcessing(
            id=self.id,
            media=self.media,
            progress=Processing(
                status="started",
                task="merge_streams",
                file_path=file_path,
            ),
        )
        await self._emit(merging)
        prc = MediaProcessor(file_path, self.ffmpeg_path)

        # Start merging
        try:
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_container=container,
            )
        except ProcessorError:
            logger.debug(
                "{} and {} don't supports merging as {}, fallback to mkv",
                video.extension,
                audio.extension,
                extension,
            )
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_container=AVContainer.MKV,
            )

        # Complete events
        merging.progress.status = "completed"
        await self._emit(merging)

        # Return merged file path
        return Path(prc.file_path)

    async def _post_process(
        self,
        file_path: Path,
        stream: Stream | None = None,
        thumbnail: Path | None = None,
        subtitles: list[Path] | None = None,
    ) -> Path:
        prc = MediaProcessor(
            file_path=file_path,
            ffmpeg_path=self.ffmpeg_path,
        )
        container = AVContainer(prc.file_path.suffix.lstrip("."))
        convert_container = (
            AVContainer(self.config.convert_to) if self.config.convert_to else None
        )

        @asynccontextmanager
        async def track_prc(task: ProcessorTask, raise_exceptions: bool = False):
            event = MediaProcessing(
                id=self.id,
                media=self.media,
                progress=Processing(
                    status="started",
                    task=task,
                    file_path=prc.file_path,
                ),
            )
            await self._emit(event)

            try:
                yield

                event.progress.file_path = prc.file_path
                event.progress.status = "completed"

                await self._emit(event)
            except ProcessorError as error:
                if raise_exceptions:
                    raise

                self.has_missing_data = True
                await self._emit(
                    MediaWarning(
                        id=self.id,
                        media=self.media,
                        message=str(error),
                    )
                )

        if isinstance(stream, VideoStream):
            if convert_container:
                async with track_prc("change_container"):
                    await prc.change_container(convert_container)

            if subtitles and container.supports_subtitles:
                async with track_prc("embed_subtitles"):
                    await prc.embed_subtitles(subtitles)

        elif isinstance(stream, AudioStream):
            if convert_container and convert_container != stream.container:
                try:
                    async with track_prc("change_container", True):
                        await prc.change_container(convert_container)
                except ProcessorError:
                    async with track_prc("convert_audio"):
                        await prc.convert_audio(container)

        # Metadata
        # Must run before embed the thumbnail.
        if self.config.embed_metadata:
            async with track_prc("embed_metadata"):
                await prc.embed_metadata(self.media)

        if thumbnail and container.supports_thumbnails:
            async with track_prc("embed_thumbnail"):
                await prc.embed_thumbnail(thumbnail, square=bool(self.media.music))

        return Path(prc.file_path)

    def _get_ffmpeg_binary(self) -> Path | None:
        if ffmpeg_path := find_internal_ffmpeg():
            logger.info("Using FFmpeg binary from dependency for post-processing")
        elif ffmpeg_path := find_system_ffmpeg():
            logger.info("Using FFmpeg binary from system for post-processing")
        else:
            logger.warning("FFmpeg binary not found, post-processing disabled")
            ffmpeg_path = None
        return ffmpeg_path

    async def _move_to_final(self, src: StrPath, dest: StrPath) -> Path:
        _src, _dest = anyio.Path(src), anyio.Path(dest)

        final_path = _dest.parent / f"{_dest.name}{_src.suffix}"
        await final_path.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move for compability between cross filesystems
        await run_sync(shutil.move, src, final_path)

        await self._emit(
            MediaCompleted(
                id=self.id,
                media=self.media,
                file_path=Path(final_path),
                result="partial" if self.has_missing_data else "success",
            )
        )

        return Path(final_path)
