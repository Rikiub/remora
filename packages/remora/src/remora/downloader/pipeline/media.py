import shutil
from collections.abc import Iterable
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
from remora.downloader.metadata import _download_subtitle, _download_thumbnail
from remora.downloader.pipeline._logs import log_event_media
from remora.downloader.pipeline.base import BaseDownloader
from remora.downloader.selector import StreamSelector
from remora.downloader.stream import BatchStreamDownloader
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
from remora.models.metadata import SubtitleList
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
)
from remora.models.stream import AudioStream, Stream, VideoStream
from remora.models.types import StrPath
from remora.path import create_temp_file
from remora.template import format_template

__all__ = ["MediaDownloader"]


@dataclass(slots=True)
class _DownloadContext:
    streams: list[StreamContext] | None = None
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class MediaDownloader(BaseDownloader[MediaState]):
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
        selected_streams = StreamSelector(
            download_options=self.download_options,
            merge_available=bool(self.ffmpeg_dir),
        ).resolve(self.media)

        if len(selected_streams) == 0:
            raise DownloaderError("Streams not found")

        primary_stream = selected_streams[0]
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
                media=self.media, streams=selected_streams
            )

        if not results.streams:
            raise ValueError("Neither video or audio was downloaded")

        # Determine stable file
        if self.ffmpeg_dir and len(results.streams) >= 2:
            file_path = await self._merge_streams(streams=results.streams)
        else:
            file_path = results.streams[0].path

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
        streams: list[Stream],
    ) -> _DownloadContext:
        if not streams:
            raise ValueError("At least one stream must be provided")

        context = _DownloadContext()

        async def download_streams():
            async with BatchStreamDownloader(
                stream=[
                    StreamContext(stream=s, path=create_temp_file()) for s in streams
                ],
                retries=self.download_options.retries,
                network_options=self.network_options,
            ) as progress:
                async for state in progress:
                    if isinstance(state, BatchStreamDownloading):
                        await self._emit(
                            MediaDownloading(
                                id=self.id,
                                media=self.media,
                                progress=state,
                            )
                        )
                    elif isinstance(state, BatchStreamCompleted):
                        context.streams = [
                            StreamContext(stream=stream, path=path)
                            for stream, path in zip(streams, state.paths)
                        ]
                        logger.debug(
                            "Streams downloaded: {paths}",
                            paths=[str(p.path) for p in context.streams],
                        )

        async def download_subtitles():
            if media.subtitles:
                subtitles = self._resolve_subtitles(media)
                paths = []

                logger.debug(
                    "Downloading {subtitles_length} subtitle with languages: {subtitles_languages}",
                    subtitles_length=len(subtitles),
                    subtitles_languages=[s.language for s in subtitles],
                )

                for sub in subtitles:
                    try:
                        path = await _download_subtitle(
                            subtitle=sub,
                            output_path=create_temp_file(),
                        )
                        paths.append(path)
                    except MetadataDownloaderError as error:
                        await self._emit(
                            MediaWarning(
                                id=self.id,
                                media=self.media,
                                message=str(error),
                            )
                        )

                context.subtitles = paths
                logger.debug("Subtitles downloaded")

        async def download_thumbnail_file():
            if media.thumbnails:
                try:
                    logger.debug("Downloading thumbnail")
                    context.thumbnail = await _download_thumbnail(
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
                tg.start_soon(download_streams)

                if self.ffmpeg_dir and self.download_options.embed_metadata:
                    tg.start_soon(download_subtitles)
                    tg.start_soon(download_thumbnail_file)
        except* DownloaderError as eg:
            raise eg.exceptions[0] from eg

        return context

    async def _merge_streams(self, streams: Iterable[StreamContext]) -> Path:
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
        logger.debug(
            "Merging {streams_extension} as '{container_extension}'",
            streams_extension=[s.extension for s in streams],
            container_extension=container.extension,
        )

        try:
            prc = await prc.merge_streams(
                streams=streams,
                merge_container=container,
            )
        except ProcessorError:
            logger.debug(
                "Streams '{streams_extension}' don't supports merging as '{container_extension}', fallback to 'mkv'",
                streams_extension=[s.extension for s in streams],
                container_extension=container.extension,
            )
            prc = await prc.merge_streams(
                streams=streams,
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

    def _resolve_subtitles(self, media: Media) -> SubtitleList:
        # Filter by language preferences
        if (requested_langs := self.download_options.languages) and (
            subtitles := media.subtitles.filter(
                language=requested_langs
            ).unique_by_language()
        ):
            return subtitles

        # Else fallback to all subtitles
        # Without the autogenerated ones
        return media.subtitles.filter(autogenerated=False).unique_by_language()

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
