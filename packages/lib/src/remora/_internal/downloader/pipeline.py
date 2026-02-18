import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import anyio
from anyio.to_thread import run_sync
from loguru import logger

from remora._internal.downloader.debug import event_debug
from remora._internal.downloader.metadata import download_subtitles, download_thumbnail
from remora._internal.downloader.selector import StreamSelector
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.extractor import MediaExtractor
from remora._internal.path import get_ffmpeg, get_tempfile
from remora._internal.processor import MediaProcessor
from remora._internal.template.output import format_template
from remora.exceptions import DownloadError, MetadataDownloadError, ProcessingError
from remora.models.download_options import DownloadOptions
from remora.models.event.media import (
    Downloading,
    Finished,
    MediaEvent,
    Resolved,
    Resolving,
    Warning,
)
from remora.models.event.process import MergeProcessing, Processing, ProcessorTask
from remora.models.event.stream import DownloadingStream, StreamEvent
from remora.models.media.item import LazyMedia, Media
from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.types import StrPath, SupportedExtensions


@dataclass(slots=True)
class DownloadContext:
    file: Path | None = None
    thumbnail: Path | None = None
    subtitles: list[Path] | None = None


class DownloadPipeline:
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        format_config: DownloadOptions | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.id = media.id

        self.media: Media = media  # type: ignore
        self.config: DownloadOptions = format_config or DownloadOptions(format="video")
        self.extractor = extractor or MediaExtractor()
        self.incomplete: bool = False

        try:
            self.ffmpeg_path = get_ffmpeg(self.config.ffmpeg_path)
        except FileNotFoundError:
            self.ffmpeg_path = None
            logger.debug("FFmpeg not founded, processing disabled")

    async def download(self) -> AsyncIterator[MediaEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[MediaEvent](30)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._producer)

                async for event in receive_stream:
                    await event_debug(event)
                    yield event

    async def _producer(self):
        with logger.contextualize(media_id=self.id, media_title=self.media.title):
            async with self._stream:
                # Resolve Data
                media = await self.resolve_media()

                # Select Streams
                video_stream, audio_stream = StreamSelector(self.config).resolve(media)

                if not self.ffmpeg_path:
                    if self.config.type == "video":
                        audio_stream = None
                    elif self.config.type == "audio":
                        video_stream = None

                stream = video_stream or audio_stream
                if not stream:
                    raise DownloadError("Streams not founded")

                # Calculate Path & Check Existence
                output = format_template(
                    self.config.template,
                    stream=stream,
                    media=media,
                    default_missing="NA",
                )
                output = anyio.Path(output)
                await output.parent.mkdir(parents=True, exist_ok=True)

                if await self.check_output_duplicate(output):
                    return

                # Download resources
                results = DownloadContext()

                async def dl_file():
                    try:
                        results.file = await self.download_streams(
                            video_stream,
                            audio_stream,
                            media.duration,
                        )
                    except* DownloadError as eg:
                        error = eg.exceptions[0]

                        await self._stream.send(
                            Warning(
                                id=self.id,
                                media=self.media,
                                message=str(error),
                            )
                        )
                        await self._stream.send(
                            Finished(
                                id=self.id,
                                media=self.media,
                                filepath=Path(),
                                result="failed",
                            )
                        )
                        raise

                async def dl_thumbnail():
                    if media.thumbnails:
                        try:
                            results.thumbnail = await download_thumbnail(
                                get_tempfile(),
                                media.thumbnails[-1],
                            )
                        except MetadataDownloadError as e:
                            await self._stream.send(
                                Warning(
                                    id=self.id,
                                    media=self.media,
                                    message=str(e),
                                )
                            )

                async def dl_subtitles():
                    if media.subtitles:
                        try:
                            results.subtitles = await download_subtitles(
                                get_tempfile(),
                                media.subtitles,
                            )
                        except MetadataDownloadError as e:
                            await self._stream.send(
                                Warning(
                                    id=self.id,
                                    media=self.media,
                                    message=str(e),
                                )
                            )

                async with anyio.create_task_group() as tg:
                    tg.start_soon(dl_file)
                    tg.start_soon(dl_thumbnail)
                    tg.start_soon(dl_subtitles)

                if results.file:
                    if self.ffmpeg_path:
                        results.file = await self.process(
                            results.file,
                            stream,
                            results.thumbnail,
                            results.subtitles,
                        )

                    # Complete (Move to target)
                    results.file = await self.move_to_final(results.file, output)
                else:
                    raise DownloadError("Final file not founded")

    async def resolve_media(self) -> Media:
        await self._stream.send(Resolving(id=self.id, media=self.media))

        media = cast(LazyMedia | Media, self.media)
        if not isinstance(media, Media):
            self.media = await self.extractor.extract(media)

        await self._stream.send(Resolved(id=self.id, media=self.media))
        return self.media

    async def check_output_duplicate(self, output: StrPath) -> Path | None:
        output = anyio.Path(output)

        async for path in output.parent.iterdir():
            if await path.is_file() and path.stem == output.name:
                path_extension = path.suffix.lstrip(".")

                if (
                    path_extension in SupportedExtensions.VIDEO
                    or path_extension in SupportedExtensions.AUDIO
                ):
                    path = Path(path)
                    await self._stream.send(
                        Finished(
                            id=self.id,
                            media=self.media,
                            filepath=path,
                            result="skipped",
                        )
                    )
                    return path

    async def download_streams(
        self,
        video_stream: VideoStream | None = None,
        audio_stream: AudioStream | None = None,
        duration: float | None = None,
    ) -> Path:
        """Orchestrates the physical download of bytes."""

        streams_events = {
            "video": DownloadingStream(
                downloaded=0,
                total=video_stream.filesize or 0 if video_stream else 0,
            ),
            "audio": DownloadingStream(
                downloaded=0,
                total=audio_stream.filesize or 0 if audio_stream else 0,
            ),
        }

        video_file = None
        audio_file = None

        async def _sync_progress(event: StreamEvent, is_video: bool):
            nonlocal video_file, audio_file

            match event.status:
                case "downloading":
                    streams_events["video" if is_video else "audio"] = event

                    v = streams_events["video"]
                    a = streams_events["audio"]

                    await self._stream.send(
                        Downloading(
                            id=self.id,
                            media=self.media,
                            downloaded=v.downloaded + a.downloaded,
                            total=v.total + a.total,
                            speed=v.speed + a.speed,
                            elapsed=max(v.elapsed, a.elapsed),
                        )
                    )
                case "finished":
                    if is_video:
                        video_file = event.filepath
                    else:
                        audio_file = event.filepath

        async def download_video():
            if video_stream:
                downloader = StreamDownloader(
                    filepath=get_tempfile(),
                    stream=video_stream,
                    duration=duration,
                )
                async for event in downloader.download():
                    await _sync_progress(event, True)

        async def download_audio():
            if audio_stream:
                downloader = StreamDownloader(
                    filepath=get_tempfile(),
                    stream=audio_stream,
                    duration=duration,
                )
                async for event in downloader.download():
                    await _sync_progress(event, False)

        try:
            async with anyio.create_task_group() as tg:
                if self.ffmpeg_path and (video_stream and audio_stream):
                    tg.start_soon(download_video)
                    tg.start_soon(download_audio)

                elif video_stream:
                    tg.start_soon(download_video)
                elif audio_stream:
                    tg.start_soon(download_audio)
        except* DownloadError as eg:
            raise eg.exceptions[0]

        # Merge if necessary
        if (
            self.ffmpeg_path
            and (video_file and video_stream)
            and (audio_file and audio_stream)
        ):
            extension = self.config.convert or "mp4"
            filepath = Path(f"{get_tempfile()}.{extension}")
            filepath.touch()

            merging = MergeProcessing(
                id=self.id,
                media=self.media,
                filepath=filepath,
                step="started",
                video_stream=video_stream,
                audio_stream=audio_stream,
            )
            await self._stream.send(merging)

            prc = MediaProcessor(filepath, self.ffmpeg_path)
            prc = await prc.merge_streams(
                streams=[(video_stream, video_file), (audio_stream, audio_file)]
            )

            merging.step = "completed"
            await self._stream.send(merging)

            return Path(prc.filepath)
        elif video_file:
            return video_file
        elif audio_file:
            return audio_file
        else:
            raise DownloadError("Streams not founded")

    async def process(
        self,
        filepath: Path,
        stream: Stream | None = None,
        thumbnail: Path | None = None,
        subtitles: list[Path] | None = None,
    ) -> Path:
        prc = MediaProcessor(filepath, self.ffmpeg_path)

        @asynccontextmanager
        async def track_prc(task: ProcessorTask, raise_exceptions: bool = False):
            event = Processing(
                id=self.id,
                media=self.media,
                filepath=prc.filepath,
                step="started",
                task=task,
            )
            await self._stream.send(event)

            try:
                yield

                event.filepath = prc.filepath
                event.step = "completed"

                await self._stream.send(event)
            except ProcessingError as error:
                if raise_exceptions:
                    raise

                self.incomplete = True
                await self._stream.send(
                    Warning(id=self.id, media=self.media, message=str(error))
                )

        # Remuxing
        if isinstance(stream, VideoStream):
            async with track_prc("change_container"):
                await prc.change_container(self.config.convert or "mp4")

            if subtitles:
                async with track_prc("embed_subtitles"):
                    await prc.embed_subtitles(subtitles)

        elif isinstance(stream, AudioStream):
            if self.config.convert and self.config.convert != stream.extension:
                try:
                    async with track_prc("change_container", True):
                        await prc.change_container(self.config.convert)
                except ProcessingError:
                    async with track_prc("convert_audio"):
                        await prc.convert_audio(self.config.convert)

        # Metadata
        # Must run before embed the thumbnail.
        if self.config.embed_metadata:
            async with track_prc("embed_metadata"):
                await prc.embed_metadata(self.media)

        if thumbnail:
            if prc.filepath.suffix[1:] in SupportedExtensions.THUMBNAIL:
                async with track_prc("embed_thumbnail"):
                    await prc.embed_thumbnail(thumbnail, square=bool(self.media.music))

        return Path(prc.filepath)

    async def move_to_final(self, src: StrPath, dest: StrPath) -> Path:
        _src, _dest = anyio.Path(src), anyio.Path(dest)

        final_path = _dest.parent / f"{_dest.name}{_src.suffix}"
        await final_path.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move for compability between cross filesystems
        await run_sync(shutil.move, src, final_path)

        await self._stream.send(
            Finished(
                id=self.id,
                media=self.media,
                filepath=Path(final_path),
                result="incomplete" if self.incomplete else "success",
            )
        )

        return Path(final_path)
