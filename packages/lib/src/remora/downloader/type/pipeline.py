import asyncio
from copy import copy
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
import time

from loguru import logger

from remora.downloader.config import FormatConfig
from remora.downloader.metadata import (
    download_format,
    download_subtitles,
    download_thumbnail,
)
from remora.downloader.selector import FormatSelector
from remora.downloader.type.debug import debug_callback
from remora.exceptions import (
    DownloadError,
    MediaError,
    MetadataDownloadError,
    ProcessingError,
)
from remora.extractor import MediaExtractor
from remora.models.content.media import LazyMedia, Media
from remora.models.format.types import AudioFormat, Format, VideoFormat
from remora.models.progress.format import FormatState
from remora.models.progress.media import (
    CompletedState,
    DownloadingState,
    MediaDownloadState,
    WarningState,
    MediaDownloadCallback,
    ResolvedState,
    ResolvingState,
    RetryingState,
)
from remora.models.progress.processor import (
    MergingProcessorState,
    ProcessorState,
    ProcessorStateType,
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
        on_progress: MediaDownloadCallback | None = None,
    ):
        self.id = media.id

        self.media = media
        self.config = format_config or FormatConfig("video")
        self.extractor = extractor or MediaExtractor()
        self.incomplete: bool = False
        self._on_progress = on_progress

        logger.debug(self.config)

    async def progress(self, state: MediaDownloadState):
        tasks = [
            asyncio.to_thread(self._on_progress, state) if self._on_progress else None,
            asyncio.to_thread(debug_callback, state),
        ]
        await asyncio.gather(*[t for t in tasks if t])

    async def run(self) -> Path:
        # Resolve Data
        media = await self.resolve_media()

        # Select Formats
        video_fmt, audio_fmt = FormatSelector(self.config).resolve(media)
        format = video_fmt or audio_fmt

        if not format:
            raise DownloadError("Formats not founded")

        #  Calculate Path & Check Existence
        output = generate_output_template(
            self.config.output,
            media,
            format=format,
            default_missing="NA",
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        if duplicate := await self.check_output_duplicate(output):
            return duplicate

        try:
            # Download File
            try:
                downloaded_file = await self.download_formats(video_fmt, audio_fmt)
            except DownloadError as e:
                if media.is_cache:
                    extractor = copy(self.extractor)
                    extractor.use_cache = False
                    self.media = await extractor.resolve(media)

                    await self.progress(WarningState(id=self.id, message=str(e)))
                    await self.progress(RetryingState(id=self.id, reason="stale_cache"))
                    return await self.run()
                raise

            if self.config.ffmpeg_path:
                # Process File
                downloaded_file = await self.process(downloaded_file, media, format)
        except MediaError as e:
            await self.progress(WarningState(id=self.id, message=str(e)))
            await self.progress(
                CompletedState(
                    id=self.id,
                    extension="",
                    reason="failed",
                )
            )
            raise

        # Complete (Move to target)
        return await self.move_to_final(downloaded_file, output)

    async def resolve_media(self) -> Media:
        await self.progress(ResolvingState(id=self.id, media=self.media))

        if not isinstance(self.media, Media):
            self.media = await self.extractor.resolve(self.media)

        await self.progress(ResolvedState(id=self.id, media=self.media))
        return self.media

    async def check_output_duplicate(self, output: Path) -> Path | None:
        def run():
            for path in output.parent.iterdir():
                if path.is_file() and path.stem == output.name:
                    path_extension = path.suffix.lstrip(".")

                    if (
                        path_extension in SupportedExtensions.video
                        or path_extension in SupportedExtensions.audio
                    ):
                        return path

        if path := await asyncio.to_thread(run):
            await self.progress(
                CompletedState(
                    id=self.id,
                    extension=path.suffix.lstrip("."),
                    reason="skipped",
                )
            )
            return path

    async def download_formats(
        self,
        video_fmt: VideoFormat | None = None,
        audio_fmt: AudioFormat | None = None,
    ) -> Path:
        """Orchestrates the physical download of bytes."""

        loop = asyncio.get_running_loop()
        progress_queue = asyncio.Queue()

        formats_states = {
            "video": FormatState(
                downloaded_bytes=0,
                total_bytes=video_fmt.filesize or 0 if video_fmt else 0,
            ),
            "audio": FormatState(
                downloaded_bytes=0,
                total_bytes=audio_fmt.filesize or 0 if audio_fmt else 0,
            ),
        }

        def _sync_progress(state: FormatState, is_video: bool):
            formats_states["video" if is_video else "audio"] = state
            loop.call_soon_threadsafe(progress_queue.put_nowait, True)

        async def _progress_consumer():
            last_update = 0
            # Target: 30 FPS = ~0.033s | 60 FPS = ~0.016s
            MIN_INTERVAL = 0.1

            while True:
                # Check queue
                if not await progress_queue.get():
                    break

                while not progress_queue.empty():
                    if not progress_queue.get_nowait():
                        return

                # Delay for fluid progress
                current_time = time.time()

                if current_time - last_update < MIN_INTERVAL:
                    progress_queue.task_done()
                    continue

                last_update = current_time

                # Send progress to callback
                v, a = formats_states["video"], formats_states["audio"]

                await self.progress(
                    DownloadingState(
                        id=self.id,
                        downloaded_bytes=v.downloaded_bytes + a.downloaded_bytes,
                        total_bytes=v.total_bytes + a.total_bytes,
                        speed=v.speed + a.speed,
                        elapsed=max(v.elapsed, a.elapsed),
                    )
                )
                progress_queue.task_done()

        def _log(format: Format):
            type = "video" if isinstance(format, VideoFormat) else "audio"
            logger.debug(
                'Downloading {type} format "{format_id}" (extension:{extension} | quality:{quality})',
                type=type,
                format_id=format.id,
                extension=format.extension,
                quality=format.quality,
            )

        video_task = None
        audio_task = None

        # Download Audio
        if audio_fmt:
            _log(audio_fmt)
            audio_task = asyncio.create_task(
                download_format(
                    get_tempfile(),
                    audio_fmt,
                    lambda s: _sync_progress(s, is_video=False),
                )
            )

        # Download Video
        if video_fmt:
            _log(video_fmt)
            video_task = asyncio.create_task(
                download_format(
                    get_tempfile(),
                    video_fmt,
                    lambda s: _sync_progress(s, is_video=True),
                )
            )

        consumer_task = asyncio.create_task(_progress_consumer())

        try:
            tasks = [t for t in [audio_task, video_task] if t is not None]
            await asyncio.gather(*tasks)
        finally:
            progress_queue.put_nowait(None)
            await consumer_task

        video_file = video_task.result() if video_task else None
        audio_file = audio_task.result() if audio_task else None

        # Merge if necessary
        if (
            self.config.ffmpeg_path
            and (video_file and video_fmt)
            and (audio_file and audio_fmt)
        ):
            extension = self.config.convert or "mp4"
            filepath = Path(f"{get_tempfile()}.{extension}")

            merging = MergingProcessorState(
                id=self.id,
                extension=filepath.suffix.lstrip("."),
                stage="started",
                video_format=video_fmt,
                audio_format=audio_fmt,
            )

            prc = await MediaProcessor.from_formats_merge(
                filepath,
                formats=[(video_fmt, video_file), (audio_fmt, audio_file)],
                ffmpeg_path=self.config.ffmpeg_path,
            )

            merging.stage = "completed"
            await self.progress(merging)

            return prc.filepath
        elif video_file:
            return video_file
        elif audio_file:
            return audio_file
        else:
            raise DownloadError("Formats not founded.")

    async def process(
        self,
        filepath: Path,
        media: Media,
        format: Format | None = None,
    ) -> Path:
        prc = MediaProcessor(filepath, self.config.ffmpeg_path)

        @asynccontextmanager
        async def track_prc(name: ProcessorStateType, raise_exceptions: bool = False):
            state = ProcessorState(
                id=self.id,
                extension=prc.filepath.suffix.lstrip("."),
                stage="started",
                processor=name,
            )
            await self.progress(state)

            try:
                yield
                state.extension = prc.filepath.suffix.lstrip(".")
                state.stage = "completed"
                await self.progress(state)
            except (ProcessingError, MetadataDownloadError) as error:
                if raise_exceptions:
                    raise

                self.incomplete = True
                await self.progress(WarningState(id=self.id, message=str(error)))

        # Remuxing
        if isinstance(format, VideoFormat):
            async with track_prc("change_container"):
                await prc.change_container(self.config.convert or "mp4")

            if media.subtitles:
                async with track_prc("embed_subtitles"):
                    subtitles = await download_subtitles(
                        get_tempfile(), media.subtitles
                    )
                    await prc.embed_subtitles(subtitles)

        elif isinstance(format, AudioFormat):
            if self.config.convert and self.config.convert != format.extension:
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
                        get_tempfile(), media.thumbnails[-1]
                    )
                    await prc.embed_thumbnail(thumbnail, square=media.is_music)

        return prc.filepath

    async def move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(shutil.move, src, final_path)

        await self.progress(
            CompletedState(
                id=self.id,
                extension=final_path.suffix.lstrip("."),
                reason="incomplete" if self.incomplete else "success",
            )
        )

        return final_path
