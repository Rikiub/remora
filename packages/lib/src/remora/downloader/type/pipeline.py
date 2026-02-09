import asyncio
from copy import copy
import shutil
from contextlib import contextmanager
from pathlib import Path

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
        self.progress = lambda d: None

        if on_progress:
            self.progress = lambda state: [
                f(state) for f in (on_progress, debug_callback)
            ]

        logger.debug(self.config)

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

        if duplicate := await self.check_output_duplicate(output, format):
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

                    self.progress(WarningState(id=self.id, message=str(e)))
                    self.progress(RetryingState(id=self.id, reason="stale_cache"))
                    return await self.run()
                raise

            if self.config.ffmpeg_path:
                # Process File
                downloaded_file = await self.process(downloaded_file, media, format)
        except MediaError as e:
            self.progress(WarningState(id=self.id, message=str(e)))
            self.progress(
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
        self.progress(ResolvingState(id=self.id, media=self.media))

        if not isinstance(self.media, Media):
            self.media = await self.extractor.resolve(self.media)

        self.progress(ResolvedState(id=self.id, media=self.media))
        return self.media

    async def check_output_duplicate(self, output: Path, format: Format) -> Path | None:
        def run():
            for path in output.parent.iterdir():
                if path.is_file() and path.stem == output.name:
                    if (
                        format.extension in SupportedExtensions.video
                        or format.extension in SupportedExtensions.audio
                    ):
                        self.progress(
                            CompletedState(
                                id=self.id,
                                extension=path.suffix.lstrip("."),
                                reason="skipped",
                            )
                        )
                        return path

        return await asyncio.to_thread(run)

    async def download_formats(
        self,
        video_fmt: VideoFormat | None = None,
        audio_fmt: AudioFormat | None = None,
    ) -> Path:
        """Orchestrates the physical download of bytes."""

        downloading = DownloadingState(id=self.id)

        video_file = None
        audio_file = None

        video_bytes = 0
        audio_bytes = 0
        total_video_bytes = 0
        total_audio_bytes = 0

        if video_fmt:
            total_video_bytes = video_fmt.filesize or 0
        if audio_fmt:
            total_audio_bytes = audio_fmt.filesize or 0

        def _update_progress(fmt_state: FormatState, is_video: bool):
            nonlocal video_bytes, audio_bytes, total_video_bytes, total_audio_bytes

            if is_video:
                video_bytes = fmt_state.downloaded_bytes
                total_video_bytes = fmt_state.total_bytes
            else:
                audio_bytes = fmt_state.downloaded_bytes
                total_audio_bytes = fmt_state.total_bytes

            downloading.downloaded_bytes = video_bytes + audio_bytes
            downloading.total_bytes = total_video_bytes + total_audio_bytes

            downloading.speed = fmt_state.speed
            downloading.elapsed = fmt_state.elapsed

            self.progress(downloading)

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
                    lambda s: _update_progress(s, is_video=False),
                )
            )

        # Download Video
        if video_fmt:
            _log(video_fmt)
            video_task = asyncio.create_task(
                download_format(
                    get_tempfile(),
                    video_fmt,
                    lambda s: _update_progress(s, is_video=True),
                )
            )

        tasks = [t for t in [audio_task, video_task] if t is not None]
        await asyncio.gather(*tasks)

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
            self.progress(merging)

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

        @contextmanager
        def track_prc(name: ProcessorStateType, raise_exceptions: bool = False):
            state = ProcessorState(
                id=self.id,
                extension=prc.filepath.suffix.lstrip("."),
                stage="started",
                processor=name,
            )
            self.progress(state)

            try:
                yield
                state.extension = prc.filepath.suffix.lstrip(".")
                state.stage = "completed"
                self.progress(state)
            except (ProcessingError, MetadataDownloadError) as error:
                if raise_exceptions:
                    raise

                self.incomplete = True
                self.progress(WarningState(id=self.id, message=str(error)))

        # Remuxing
        if isinstance(format, VideoFormat):
            with track_prc("change_container"):
                await prc.change_container(self.config.convert or "mp4")

            if media.subtitles:
                with track_prc("embed_subtitles"):
                    subtitles = await download_subtitles(
                        get_tempfile(), media.subtitles
                    )
                    await prc.embed_subtitles(subtitles)

        elif isinstance(format, AudioFormat):
            if self.config.convert and self.config.convert != format.extension:
                try:
                    with track_prc("change_container", True):
                        await prc.change_container(self.config.convert)
                except ProcessingError:
                    with track_prc("convert_audio"):
                        await prc.convert_audio(self.config.convert)

        # Metadata
        # Must run before embed the thumbnail.
        if self.config.embed_metadata:
            with track_prc("embed_metadata"):
                await prc.embed_metadata(media, media.is_music)

        if media.thumbnails:
            if prc.filepath.suffix[1:] in ThumbnailSupport:
                with track_prc("embed_thumbnail"):
                    thumbnail = await download_thumbnail(
                        get_tempfile(), media.thumbnails[-1]
                    )
                    await prc.embed_thumbnail(thumbnail, square=media.is_music)

        return prc.filepath

    async def move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(shutil.move, src, final_path)

        self.progress(
            CompletedState(
                id=self.id,
                extension=final_path.suffix.lstrip("."),
                reason="incomplete" if self.incomplete else "success",
            )
        )

        return final_path
