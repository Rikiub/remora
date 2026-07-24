import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import anyio
from anyio.to_thread import run_sync
from loguru import logger

from remora._internal.downloader.logs import log_event_media
from remora._internal.downloader.metadata import download_subtitles, download_thumbnail
from remora._internal.downloader.selector import StreamSelector
from remora._internal.downloader.stream.batch import BatchStreamDownloader
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.extractor import MediaExtractor
from remora._internal.path import get_ffmpeg, get_tempfile
from remora._internal.processor import MediaProcessor
from remora._internal.template.output import format_template
from remora.exceptions import DownloaderError, MetadataDownloaderError, ProcessorError
from remora.models.container.extension.audio import AudioExtension
from remora.models.container.extension.types import get_extension
from remora.models.container.extension.video import VideoExtension
from remora.models.download_options import DownloadOptions
from remora.models.event.media import (
    MediaCancelled,
    MediaCompleted,
    MediaDownloading,
    MediaEvent,
    MediaExtracting,
    MediaFailed,
    MediaProcessing,
    MediaWarning,
)
from remora.models.event.process import Processing, ProcessorTask
from remora.models.event.stream import BatchStreamDownloading
from remora.models.media.item import LazyMedia, Media
from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.types import StrPath


@dataclass(slots=True)
class DownloadContext:
    file_path: Path = Path()
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class DownloadPipeline:
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.id = media.id

        self.media: Media = media  # type: ignore
        self.config = config or DownloadOptions()
        self.extractor = extractor or MediaExtractor()
        self.has_missing_data = False

        try:
            self.ffmpeg_path = get_ffmpeg(self.config.ffmpeg_path)
        except FileNotFoundError:
            self.ffmpeg_path = None
            logger.debug("FFmpeg not founded, processing disabled")

    async def download(self) -> AsyncIterator[MediaEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[MediaEvent](30)

        async with receive_stream:
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._producer)

                    async for event in receive_stream:
                        await log_event_media(event)
                        yield event
            except anyio.get_cancelled_exc_class():
                yield MediaCancelled(id=self.id, media=self.media)
                raise

    async def _producer(self):
        with logger.contextualize(media_id=self.id):
            async with self._stream:
                # Resolve Media
                media = await self.resolve_media()

                with logger.contextualize(media_title=media.title):
                    # Select Streams
                    video_stream, audio_stream = StreamSelector(self.config).resolve(
                        media
                    )

                    if not self.ffmpeg_path:
                        if self.config.format_type == "video":
                            audio_stream = None
                        elif self.config.format_type == "audio":
                            video_stream = None

                    stream = video_stream or audio_stream
                    if not stream:
                        raise DownloaderError("Streams not founded")

                    # Calculate Path & Check Existence
                    output = format_template(
                        self.config.output_template,
                        stream=stream,
                        media=media,
                        default_missing="NA",
                    )
                    output = anyio.Path(output)
                    await output.parent.mkdir(parents=True, exist_ok=True)

                    if await self.check_output_duplicate(output):
                        return

                    with logger.contextualize(status="downloading"):
                        results = await self.download_resources(
                            media,
                            video_stream,
                            audio_stream,
                        )

                    if self.ffmpeg_path:
                        with logger.contextualize(status="processing"):
                            results.file_path = await self.process(
                                results.file_path,
                                stream,
                                results.thumbnail,
                                results.subtitles,
                            )

                    # Complete (Move to target)
                    results.file_path = await self.move_to_final(
                        results.file_path, output
                    )

    async def resolve_media(self) -> Media:
        await self._stream.send(MediaExtracting(id=self.id, media=self.media))

        media = cast(LazyMedia | Media, self.media)
        if not isinstance(media, Media):
            self.media = await self.extractor.extract(media)

        return self.media

    async def check_output_duplicate(self, output: StrPath) -> Path | None:
        output = anyio.Path(output)

        async for path in output.parent.iterdir():
            if await path.is_file() and path.stem == output.name:
                extension = get_extension(path.suffix.lstrip("."))

                if isinstance(extension, (VideoExtension, AudioExtension)):
                    path = Path(path)
                    await self._stream.send(
                        MediaCompleted(
                            id=self.id,
                            media=self.media,
                            file_path=path,
                            result="duplicate",
                        )
                    )
                    return path

    async def download_resources(
        self,
        media: Media,
        video_stream: VideoStream | None,
        audio_stream: AudioStream | None,
    ) -> DownloadContext:
        results = DownloadContext()

        async def file():
            if not (video_stream or audio_stream):
                raise ValueError("Streams not found")

            try:
                if video_stream and audio_stream:
                    completed_event = None

                    async for event in BatchStreamDownloader(
                        video=(video_stream, get_tempfile()),
                        audio=(audio_stream, get_tempfile()),
                    ).download():
                        if event.status == "downloading":
                            await self._stream.send(
                                MediaDownloading(
                                    id=self.id,
                                    media=self.media,
                                    progress=event,
                                )
                            )
                        elif event.status == "completed":
                            completed_event = event

                    if not completed_event:
                        raise ValueError()

                    if self.ffmpeg_path:
                        results.file_path = await self.process_merge(
                            video=(video_stream, completed_event.video_path),
                            audio=(audio_stream, completed_event.audio_path),
                        )
                    elif p := completed_event.video_path:
                        results.file_path = p
                    elif p := completed_event.audio_path:
                        results.file_path = p
                    else:
                        raise DownloaderError("Streams not founded")

                    logger.debug(
                        'Stream downloaded: "{file}"',
                        file=results.file_path,
                    )
                else:
                    async for event in StreamDownloader(
                        output_path=get_tempfile(),
                        stream=video_stream or audio_stream,  # type: ignore
                    ).download():
                        if event.status == "downloading":
                            await self._stream.send(
                                MediaDownloading(
                                    id=self.id,
                                    media=self.media,
                                    progress=BatchStreamDownloading(streams=[event]),
                                )
                            )
                        elif event.status == "completed":
                            results.file_path = event.file_path
            except* (DownloaderError, ProcessorError) as eg:
                error = eg.exceptions[0]
                logger.debug(
                    "Unable to download streams: {error}",
                    error=str(error),
                )

                await self._stream.send(
                    MediaFailed(
                        id=self.id,
                        media=self.media,
                        message=str(error),
                    )
                )
                raise error

        async def thumbnail():
            if media.thumbnails:
                try:
                    logger.debug("Downloading thumbnail")
                    results.thumbnail = await download_thumbnail(
                        media.thumbnails[0],
                        get_tempfile(),
                    )
                    logger.debug("Thumbnail downloaded")
                except MetadataDownloaderError as e:
                    await self._stream.send(
                        MediaWarning(
                            id=self.id,
                            media=self.media,
                            message=str(e),
                        )
                    )

        async def subtitles():
            if media.subtitles:
                try:
                    logger.debug("Downloading subtitles")
                    results.subtitles = await download_subtitles(
                        media.subtitles,
                        get_tempfile(),
                    )
                    logger.debug("Subtitles downloaded")
                except MetadataDownloaderError as e:
                    await self._stream.send(
                        MediaWarning(
                            id=self.id,
                            media=self.media,
                            message=str(e),
                        )
                    )

        async with anyio.create_task_group() as tg:
            tg.start_soon(file)
            tg.start_soon(thumbnail)
            tg.start_soon(subtitles)

        return results

    async def process_merge(
        self,
        video: tuple[VideoStream, Path],
        audio: tuple[AudioStream, Path],
    ):
        extension = VideoExtension.MP4
        if isinstance(self.config.format_target, VideoExtension):
            extension = self.config.format_target

        file_path = Path(f"{get_tempfile()}.{extension}")
        file_path.touch()

        merging = MediaProcessing(
            id=self.id,
            media=self.media,
            progress=Processing(
                status="started",
                task="merge_streams",
                file_path=file_path,
            ),
        )
        await self._stream.send(merging)

        prc = MediaProcessor(file_path, self.ffmpeg_path)

        try:
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_format=extension,
            )
        except ProcessorError:
            logger.debug(
                "{} and {} don't supports merging as {}, fallback to mkv",
                video[0].extension,
                audio[0].extension,
                extension,
            )
            prc = await prc.merge_streams(
                video=video,
                audio=audio,
                merge_format=VideoExtension.MKV,
            )

        merging.progress.status = "completed"
        await self._stream.send(merging)

        return Path(prc.file_path)

    async def process(
        self,
        file_path: Path,
        stream: Stream | None = None,
        thumbnail: Path | None = None,
        subtitles: list[Path] | None = None,
    ) -> Path:
        prc = MediaProcessor(file_path, self.ffmpeg_path)

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
            await self._stream.send(event)

            try:
                yield

                event.progress.file_path = prc.file_path
                event.progress.status = "completed"

                await self._stream.send(event)
            except ProcessorError as error:
                if raise_exceptions:
                    raise

                self.has_missing_data = True
                await self._stream.send(
                    MediaWarning(
                        id=self.id,
                        media=self.media,
                        message=str(error),
                    )
                )

        if isinstance(stream, VideoStream):
            if self.config.format_target:
                async with track_prc("change_container"):
                    await prc.change_container(self.config.format_target)

            if subtitles:
                async with track_prc("embed_subtitles"):
                    await prc.embed_subtitles(subtitles)

        elif isinstance(stream, AudioStream):
            if (
                self.config.format_target
                and self.config.format_target != stream.extension
            ):
                try:
                    async with track_prc("change_container", True):
                        await prc.change_container(self.config.format_target)
                except ProcessorError:
                    async with track_prc("convert_audio"):
                        await prc.convert_audio(self.config.format_target)

        # Metadata
        # Must run before embed the thumbnail.
        if self.config.embed_metadata:
            async with track_prc("embed_metadata"):
                await prc.embed_metadata(self.media)

        if thumbnail:
            extension = get_extension(prc.file_path.suffix.lstrip("."))

            if extension.supports_thumbnails:
                async with track_prc("embed_thumbnail"):
                    await prc.embed_thumbnail(thumbnail, square=bool(self.media.music))

        return Path(prc.file_path)

    async def move_to_final(self, src: StrPath, dest: StrPath) -> Path:
        _src, _dest = anyio.Path(src), anyio.Path(dest)

        final_path = _dest.parent / f"{_dest.name}{_src.suffix}"
        await final_path.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move for compability between cross filesystems
        await run_sync(shutil.move, src, final_path)

        await self._stream.send(
            MediaCompleted(
                id=self.id,
                media=self.media,
                file_path=Path(final_path),
                result="partial" if self.has_missing_data else "success",
            )
        )

        return Path(final_path)
