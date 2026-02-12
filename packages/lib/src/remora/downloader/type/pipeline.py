import pathlib
import shutil
from contextlib import asynccontextmanager
from copy import copy
from typing import AsyncIterator

import anyio
from anyio import Path
from anyio.to_thread import run_sync
from loguru import logger
from remora.downloader.config import FormatConfig
from remora.downloader.stream.main import StreamDownloader
from remora.downloader.metadata import download_subtitles, download_thumbnail
from remora.downloader.selector import StreamSelector
from remora.downloader.type.debug import debug_callback
from remora.exceptions import (
    DownloadError,
    MediaError,
    MetadataDownloadError,
    ProcessingError,
)
from remora.extractor import MediaExtractor
from remora.models.content.media import LazyMedia, Media
from remora.models.stream.types import AudioStream, Stream, VideoStream
from remora.models.event.stream import DownloadingStream, StreamEvent
from remora.models.event.media import (
    Finished,
    Downloading,
    MediaEvent,
    Resolved,
    Resolving,
    Retrying,
    Warning,
)
from remora.models.event.processor import (
    MergingProcessor,
    Processor,
    ProcessorTask,
)
from remora.path import get_tempfile
from remora.processor import MediaProcessor
from remora.template.parser import generate_output_template
from remora.ydl.types import SupportedExtensions, ThumbnailSupport


class DownloadPipeline:
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        format_config: FormatConfig | None = None,
        extractor: MediaExtractor | None = None,
    ):
        self.id = media.id

        self.media: Media = media  # type: ignore
        self.config = format_config or FormatConfig("video")
        self.extractor = extractor or MediaExtractor()
        self.incomplete: bool = False

        logger.debug(self.config)

    async def run(self) -> AsyncIterator[MediaEvent]:
        self._stream, receive_stream = anyio.create_memory_object_stream[MediaEvent](30)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._execute_download)

                async for event in receive_stream:
                    await debug_callback(event)
                    yield event

    async def _execute_download(self):
        async with self._stream:
            # Check ffmpeg existence
            try:
                await self.config.validate_ffmpeg()
            except FileNotFoundError as e:
                raise ProcessingError(str(e)) from e

            # Resolve Data
            media = await self.resolve_media()

            # Select Streams
            video_stream, audio_stream = StreamSelector(self.config).resolve(media)
            stream = video_stream or audio_stream

            if not stream:
                raise DownloadError("Streams not founded")

            #  Calculate Path & Check Existence
            output = generate_output_template(
                self.config.output,
                media,
                stream=stream,
                default_missing="NA",
            )
            output = Path(output)
            await output.parent.mkdir(parents=True, exist_ok=True)

            if await self.check_output_duplicate(output):
                return

            try:
                # Download File
                try:
                    downloaded_file = await self.download_streams(
                        video_stream, audio_stream, media.duration
                    )
                except DownloadError as e:
                    if media.is_cache:
                        extractor = copy(self.extractor)
                        extractor.use_cache = False
                        self.media = await extractor.resolve(media)

                        self._stream.send_nowait(
                            Warning(id=self.id, media=self.media, message=str(e))
                        )
                        self._stream.send_nowait(
                            Retrying(id=self.id, media=self.media, result="stale_cache")
                        )
                    raise

                if self.config.ffmpeg_path:
                    # Process File
                    downloaded_file = await self.process(downloaded_file, media, stream)
            except MediaError as e:
                self._stream.send_nowait(
                    Warning(id=self.id, media=self.media, message=str(e))
                )
                self._stream.send_nowait(
                    Finished(
                        id=self.id,
                        media=self.media,
                        filepath=pathlib.Path(),
                        result="failed",
                    )
                )
                raise

            # Complete (Move to target)
            await self.move_to_final(downloaded_file, output)

    async def resolve_media(self) -> Media:
        self._stream.send_nowait(Resolving(id=self.id, media=self.media))

        if not isinstance(self.media, Media):
            self.media = await self.extractor.resolve(self.media)

        self._stream.send_nowait(Resolved(id=self.id, media=self.media))
        return self.media

    async def check_output_duplicate(self, output: Path) -> Path | None:
        async for path in output.parent.iterdir():
            if await path.is_file() and path.stem == output.name:
                path_extension = path.suffix.lstrip(".")

                if (
                    path_extension in SupportedExtensions.video
                    or path_extension in SupportedExtensions.audio
                ):
                    self._stream.send_nowait(
                        Finished(
                            id=self.id,
                            media=self.media,
                            filepath=pathlib.Path(path),
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

        streams_states = {
            "video": DownloadingStream(
                downloaded_bytes=0,
                total_bytes=video_stream.filesize or 0 if video_stream else 0,
            ),
            "audio": DownloadingStream(
                downloaded_bytes=0,
                total_bytes=audio_stream.filesize or 0 if audio_stream else 0,
            ),
        }

        video_file = None
        audio_file = None

        async def _sync_progress(event: StreamEvent, is_video: bool):
            nonlocal video_file, audio_file

            match event.status:
                case "downloading":
                    streams_states["video" if is_video else "audio"] = event

                    v = streams_states["video"]
                    a = streams_states["audio"]

                    self._stream.send_nowait(
                        Downloading(
                            id=self.id,
                            media=self.media,
                            downloaded_bytes=v.downloaded_bytes + a.downloaded_bytes,
                            total_bytes=v.total_bytes + a.total_bytes,
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
                    filepath=await get_tempfile(),
                    stream=video_stream,
                    duration=duration,
                )
                async for event in downloader.download():
                    await _sync_progress(event, True)

        async def download_audio():
            if audio_stream:
                downloader = StreamDownloader(
                    filepath=await get_tempfile(),
                    stream=audio_stream,
                    duration=duration,
                )
                async for event in downloader.download():
                    await _sync_progress(event, False)

        async with anyio.create_task_group() as tg:
            # Download Audio
            if audio_stream:
                tg.start_soon(download_audio)

            # Download Video
            if video_stream:
                tg.start_soon(download_video)

        # Merge if necessary
        if (
            self.config.ffmpeg_path
            and (video_file and video_stream)
            and (audio_file and audio_stream)
        ):
            extension = self.config.convert or "mp4"
            filepath = pathlib.Path(f"{await get_tempfile()}.{extension}")

            merging = MergingProcessor(
                id=self.id,
                media=self.media,
                filepath=filepath,
                step="started",
                video_stream=video_stream,
                audio_stream=audio_stream,
            )

            prc = await MediaProcessor.from_streams_merge(
                filepath,
                streams=[(video_stream, video_file), (audio_stream, audio_file)],
                ffmpeg_path=self.config.ffmpeg_path,
            )

            merging.step = "completed"
            self._stream.send_nowait(merging)

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
        media: Media,
        stream: Stream | None = None,
    ) -> Path:
        prc = MediaProcessor(filepath, self.config.ffmpeg_path)

        @asynccontextmanager
        async def track_prc(task: ProcessorTask, raise_exceptions: bool = False):
            event = Processor(
                id=self.id,
                media=self.media,
                filepath=prc.filepath,
                step="started",
                task=task,
            )
            self._stream.send_nowait(event)

            try:
                yield

                event.filepath = prc.filepath
                event.step = "completed"

                self._stream.send_nowait(event)
            except (ProcessingError, MetadataDownloadError) as error:
                if raise_exceptions:
                    raise

                self.incomplete = True
                self._stream.send_nowait(
                    Warning(id=self.id, media=self.media, message=str(error))
                )

        # Remuxing
        if isinstance(stream, VideoStream):
            async with track_prc("change_container"):
                await prc.change_container(self.config.convert or "mp4")

            if media.subtitles:
                async with track_prc("embed_subtitles"):
                    subtitles = await download_subtitles(
                        await get_tempfile(), media.subtitles
                    )
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
                await prc.embed_metadata(media, media.is_music)

        if media.thumbnails:
            if prc.filepath.suffix[1:] in ThumbnailSupport:
                async with track_prc("embed_thumbnail"):
                    thumbnail = await download_thumbnail(
                        await get_tempfile(),
                        media.thumbnails[-1],
                    )
                    await prc.embed_thumbnail(thumbnail, square=media.is_music)

        return Path(prc.filepath)

    async def move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        await final_path.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move for compability between cross filesystems
        await run_sync(shutil.move, src, final_path)

        self._stream.send_nowait(
            Finished(
                id=self.id,
                media=self.media,
                filepath=pathlib.Path(final_path),
                result="incomplete" if self.incomplete else "success",
            )
        )

        return final_path
