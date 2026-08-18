import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import anyio
from anyio.to_thread import run_sync
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.logs import log_event_media
from remora._internal.downloader.metadata import download_subtitles, download_thumbnail
from remora._internal.downloader.pipeline.base import Downloader
from remora._internal.downloader.selector import StreamSelector
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.downloader.stream.muxed import MuxedStreamDownloader
from remora._internal.extractor import MediaExtractor
from remora._internal.ffmpeg import (
    find_system_ffmpeg_dir,
    find_wheel_ffmpeg_dir,
)
from remora._internal.path import create_temp_file
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
from remora.models.media import LazyMedia, Media
from remora.models.progress import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    MediaCancelled,
    MediaCompleted,
    MediaDownloading,
    MediaEnded,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaSkipped,
    MediaStarted,
    MediaState,
    MediaWarning,
    Processing,
    ProcessorTask,
    StreamProgressState,
)
from remora.models.stream import AudioStream, Stream, VideoStream
from remora.types import StrPath


@dataclass(slots=True)
class DownloadContext:
    video: StreamContext[VideoStream] | None = None
    audio: StreamContext[AudioStream] | None = None
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class MediaDownloader(Downloader[MediaState]):
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        super().__init__(config=config, extractor=extractor)

        self.id: str = media.id
        self.media: Media = media  # ty: ignore[invalid-assignment]
        self._unresolved_item = media

        self.ffmpeg_dir = self._determine_ffmpeg_dir()
        self.has_missing_data = False

    async def _resolve_media(self) -> None:
        item = self._unresolved_item

        if type(item) is LazyMedia:
            await self._emit(MediaExtracting(id=item.id, media=item))
            item = await self.extractor.extract(item)

            self.id = item.id
            self.media = item

    @override
    async def _run_pipeline(self):
        try:
            await self._emit(MediaStarted(id=self.id, media=self.media))
            await self._resolve_media()

            with logger.contextualize(media_id=self.id, media_title=self.media.title):
                await self._pipeline()
        except (DownloaderError, ExtractorError, ProcessorError) as error:
            await self._emit(
                MediaFailed(
                    id=self.id,
                    media=self.media,
                    message=str(error),
                )
            )
        finally:
            await self._emit(
                MediaEnded(
                    id=self.id,
                    media=self.media,
                )
            )

    @override
    async def _on_cancelled(self):
        await self._emit(MediaCancelled(id=self.id, media=self.media))
        await self._emit(
            MediaEnded(
                id=self.id,
                media=self.media,
            )
        )

    @override
    async def _emit(self, state) -> None:
        """Safely dispatches and logs pipeline events."""
        await log_event_media(state)
        await super()._emit(state)

    async def _pipeline(self):
        """The one who orchestrate the jobs."""

        # Select Best Streams
        selected = StreamSelector(
            self.config,
            merge_available=bool(self.ffmpeg_dir),
        ).resolve(self.media)

        metadata_stream = selected.muxed or selected.video or selected.audio
        if not metadata_stream:
            raise DownloaderError("Streams not found")

        # Calculate Path & Check Existence
        output = format_template(
            self.config.output_template,
            stream=metadata_stream,
            media=self.media,
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
                self.media,
                selected.muxed or selected.video,
                selected.audio,
            )

        # Determine stable file
        if self.ffmpeg_dir and (results.video and results.audio):
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
        if self.ffmpeg_dir:
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
                    message="FFmpeg binaries unavailable, skipping post-processing",
                )
            )

        # Complete (Move file to target)
        await self._move_to_final(file_path, output)

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
                    MediaSkipped(
                        id=self.id,
                        media=self.media,
                        file_path=path,
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
                        path=create_temp_file(),
                    ),
                    audio=StreamContext(
                        stream=audio_stream,
                        path=create_temp_file(),
                    ),
                )
            else:
                downloader = StreamDownloader(
                    output_path=create_temp_file(),
                    stream=video_stream or audio_stream,  # ty: ignore[invalid-argument-type]
                )

            async with downloader as progress:
                async for state in progress:
                    if state.status == "downloading":
                        # Normalize single downloads
                        if isinstance(state, StreamProgressState):
                            state = BatchStreamDownloading(streams=[state])

                        await self._emit(
                            MediaDownloading(
                                id=self.id,
                                media=self.media,
                                progress=state,
                            )
                        )
                    elif state.status == "completed":
                        if video_stream:
                            context.video = StreamContext(
                                stream=video_stream,
                                path=state.video_path
                                if isinstance(state, BatchStreamCompleted)
                                else state.file_path,
                            )
                        elif audio_stream:
                            context.audio = StreamContext(
                                stream=audio_stream,
                                path=state.audio_path
                                if isinstance(state, BatchStreamCompleted)
                                else state.file_path,
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

        async def thumbnail():
            if media.thumbnails:
                try:
                    logger.debug("Downloading thumbnail")
                    context.thumbnail = await download_thumbnail(
                        media.thumbnails[0],
                        create_temp_file(),
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
                        media.subtitles.externals(),
                        create_temp_file(),
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

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(format)
                tg.start_soon(thumbnail)
                tg.start_soon(subtitles)
        except* DownloaderError as eg:
            raise eg.exceptions[0] from eg

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
        file_path = Path(f"{create_temp_file()}.{extension}")
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
        prc = MediaProcessor(file_path, self.ffmpeg_dir)

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
            ffmpeg_dir=self.ffmpeg_dir,
        )
        container = AVContainer(prc.file_path.suffix.lstrip("."))
        convert_container = (
            AVContainer(self.config.convert_to) if self.config.convert_to else None
        )

        @asynccontextmanager
        async def track_prc(task: ProcessorTask, raise_exceptions: bool = False):
            state = MediaProcessing(
                id=self.id,
                media=self.media,
                progress=Processing(
                    status="started",
                    task=task,
                    file_path=prc.file_path,
                ),
            )
            await self._emit(state)

            try:
                yield

                state.progress.file_path = prc.file_path
                state.progress.status = "completed"

                await self._emit(state)
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

    def _determine_ffmpeg_dir(self) -> Path | None:
        if ffmpeg_dir := self.config.ffmpeg_location:
            logger.info('Using "ffmpeg" and "ffprobe" binaries from provided path')
        elif ffmpeg_dir := find_wheel_ffmpeg_dir():
            logger.info(
                'Using "ffmpeg" and "ffprobe" binaries from wheel for post-processing'
            )
        elif ffmpeg_dir := find_system_ffmpeg_dir():
            logger.info(
                'Using "ffmpeg" and "ffprobe" binaries from system for post-processing'
            )
        else:
            logger.warning("FFmpeg location not found, post-processing disabled")
            ffmpeg_dir = None
        return Path(ffmpeg_dir) if ffmpeg_dir else None

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
