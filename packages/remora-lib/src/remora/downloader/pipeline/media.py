import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import anyio
from anyio.to_thread import run_sync
from loguru import logger
from typing_extensions import override

from remora import ffmpeg, processor
from remora._types import StreamContext
from remora.constants import DEFAULT_AUDIO_CONTAINER, DEFAULT_VIDEO_CONTAINER
from remora.downloader.metadata import download_subtitles, download_thumbnail
from remora.downloader.pipeline._logs import log_event_media
from remora.downloader.pipeline.base import Downloader
from remora.downloader.selector import StreamSelector
from remora.downloader.stream import MuxedStreamDownloader, StreamDownloader
from remora.exceptions import (
    DownloaderError,
    ExtractorError,
    MetadataDownloaderError,
    ProcessorError,
)
from remora.models import VideoContainer
from remora.models.container import (
    AudioContainer,
)
from remora.models.container.av import get_container
from remora.models.media import Media
from remora.models.options.download import DownloadOptions
from remora.models.options.network import NetworkOptions
from remora.models.progress import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    MediaCancelled,
    MediaCompleted,
    MediaDownloading,
    MediaEnded,
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
from remora.models.types import StrPath
from remora.path import create_temp_file
from remora.template import format_template

__all__ = ["MediaDownloader"]


@dataclass(slots=True)
class _DownloadContext:
    video: StreamContext[VideoStream] | None = None
    audio: StreamContext[AudioStream] | None = None
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class MediaDownloader(Downloader[MediaState]):
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: Media,
        download_options: DownloadOptions | None = None,
        network_options: NetworkOptions | None = None,
    ):
        super().__init__(download_options=download_options)
        self.network_options = network_options

        self.id: str = media.id
        self.media: Media = media

        self.ffmpeg_dir = self._determine_ffmpeg_dir()
        self.has_missing_data = False

    @override
    async def _run_pipeline(self):
        with logger.contextualize(media_id=self.id, media_title=self.media.title):
            try:
                await self._emit(MediaStarted(id=self.id, media=self.media))
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
            self.download_options,
            merge_available=bool(self.ffmpeg_dir),
        ).resolve(self.media)

        primary_stream = selected.muxed or selected.video or selected.audio
        if not primary_stream:
            raise DownloaderError("Streams not found")

        logger.debug(
            "Primary selected stream: {selected_stream}",
            selected_stream=type(primary_stream).__name__,
        )

        # Calculate Path & Check Existence
        output = format_template(
            self.download_options.output_template,
            stream=primary_stream,
            media=self.media,
            default_missing="NA",
        )
        output = anyio.Path(output)
        await output.parent.mkdir(parents=True, exist_ok=True)

        # Skip if option is enabled and a duplicate is found
        if self.download_options.skip_existing and await self._check_output_duplicate(
            output, type(primary_stream)
        ):
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
            file_path = await self._merge_streams(
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
                    primary_stream,
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

    async def _check_output_duplicate(
        self,
        output: StrPath,
        stream_type: type[Stream],
    ) -> Path | None:
        output = anyio.Path(output)

        async for path in output.parent.iterdir():
            if (
                # File name match
                await path.is_file()
                and path.stem == output.name
                # Normalize file extension
                and (container := get_container(path.suffix.lstrip(".")))
            ):
                file_type = (
                    AudioStream
                    if isinstance(container, AudioContainer)
                    else VideoStream
                )

                if stream_type == file_type:
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
    ) -> _DownloadContext:
        context = _DownloadContext()

        async def streams():
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

        try:
            async with anyio.create_task_group() as tg:
                name = self.__class__.__name__
                tg.start_soon(streams, name=f"{name}.streams({self.id})")
                tg.start_soon(subtitles, name=f"{name}.subtitles({self.id})")
                tg.start_soon(thumbnail, name=f"{name}.thumbnail({self.id})")
        except* DownloaderError as eg:
            raise eg.exceptions[0] from eg

        return context

    async def _merge_streams(
        self,
        video: StreamContext[VideoStream],
        audio: StreamContext[AudioStream],
    ) -> Path:
        # Get container and extension
        try:
            convert = get_container(self.download_options.convert_to)
            if not isinstance(convert, VideoContainer):
                raise TypeError(convert)
            container = convert
        except (ValueError, TypeError):
            container = VideoContainer(DEFAULT_VIDEO_CONTAINER)

        # Setup events
        file_path = Path(f"{create_temp_file()}.{container.extension}")
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
        prc = processor.MediaProcessor(file_path, self.ffmpeg_dir)

        # Start merging
        try:
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_container=container,
            )
        except ProcessorError:
            logger.debug(
                "'{video_extension}' and '{audio_extension}' don't supports merging as '{container_extension}', fallback to 'mkv'",
                video_extension=video.extension,
                audio_extension=audio.extension,
                container_extension=container.extension,
            )
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_container=VideoContainer.MKV,
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
        prc = processor.MediaProcessor(
            file_path=file_path,
            ffmpeg_dir=self.ffmpeg_dir,
        )
        convert_container = (
            get_container(self.download_options.convert_to)
            if self.download_options.convert_to
            else None
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
            # If user requested a container, then convert to it.
            if convert_container:
                async with track_prc("change_container"):
                    await prc.change_container(convert_container)

            # If user requested audio and there is only a VideoStream, then extract audio from it.
            elif self.download_options.format_type == "audio":
                async with track_prc("convert_audio"):
                    await prc.convert_audio(AudioContainer(DEFAULT_AUDIO_CONTAINER))

            if subtitles and prc.file_container.supports_subtitles:
                async with track_prc("embed_subtitles"):
                    await prc.embed_subtitles(subtitles)

        elif (
            isinstance(stream, AudioStream)
            and isinstance(convert_container, AudioContainer)
            and convert_container != stream.container
        ):
            try:
                async with track_prc("change_container", True):
                    await prc.change_container(convert_container)
            except ProcessorError:
                async with track_prc("convert_audio"):
                    await prc.convert_audio(convert_container)

        # Metadata
        # Must run before embed the thumbnail.
        if self.download_options.embed_metadata:
            async with track_prc("embed_metadata"):
                await prc.embed_metadata(self.media)

        if thumbnail and prc.file_container.supports_thumbnails:
            async with track_prc("embed_thumbnail"):
                await prc.embed_thumbnail(thumbnail, square=bool(self.media.music))

        return Path(prc.file_path)

    def _determine_ffmpeg_dir(self) -> Path | None:
        if ffmpeg_dir := self.download_options.ffmpeg_location:
            logger.info('Using "ffmpeg" and "ffprobe" binaries from provided path')
        elif ffmpeg_dir := ffmpeg.find_wheel_ffmpeg_dir():
            logger.info(
                'Using "ffmpeg" and "ffprobe" binaries from wheel for post-processing'
            )
        elif ffmpeg_dir := ffmpeg.find_system_ffmpeg_dir():
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
