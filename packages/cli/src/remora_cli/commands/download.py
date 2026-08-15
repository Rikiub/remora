from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from cyclopts import App, CycloptsError, Parameter
from loguru import logger

from remora.models.container import AVContainerFormat, RichAVContainer
from remora.types import DEFAULT_TEMPLATE, DEFAULT_WORKERS, VideoQuality
from remora_cli.options import (
    DisplayOptions,
    ExtractorOptions,
    QueryParameter,
)
from remora_cli.ui.rich import CONSOLE


class Panel(StrEnum):
    FILTERS = "Filters"
    DOWNLOADER = "Downloader"
    POST_PROCESS = "Post-processing"


app = App()


@app.command
async def download(
    # ARGUMENTS
    query: QueryParameter,
    # FILTER
    type: Annotated[
        AVContainerFormat | None,
        Parameter(
            help="Type of stream to download (downloads best by default).",
            short_alias=True,
            show_default=False,
            group=Panel.FILTERS,
        ),
    ] = None,
    quality: Annotated[
        int | VideoQuality | None,
        Parameter(
            help="Prefered target quality.",
            short_alias=True,
            group=Panel.FILTERS,
        ),
    ] = None,
    video_codec: Annotated[
        str | None,
        Parameter(
            help="Prefered video codec.",
            alias="--vcodec",
            group=Panel.FILTERS,
        ),
    ] = None,
    audio_codec: Annotated[
        str | None,
        Parameter(
            help="Prefered audio codec.",
            alias="--acodec",
            group=Panel.FILTERS,
        ),
    ] = None,
    # DOWNLOADER
    output: Annotated[
        str | Path,
        Parameter(
            help="Path or template for the saved file.",
            short_alias=True,
            group=Panel.DOWNLOADER,
        ),
    ] = DEFAULT_TEMPLATE,
    skip_existing: Annotated[
        bool,
        Parameter(
            help="Skip downloading if a file with the same name already exists, regardless of extension.",
            group=Panel.DOWNLOADER,
            negative=False,
            negative_alias="--overwrite",
        ),
    ] = True,
    max_workers: Annotated[
        int,
        Parameter(
            help="Limit of simultaneous downloads.",
            group=Panel.DOWNLOADER,
        ),
    ] = DEFAULT_WORKERS,
    limit_rate: Annotated[
        str | None,
        Parameter(
            help="Maximum download rate (e.g. [green]5M[/] or [green]500K[/]).",
            group=Panel.DOWNLOADER,
        ),
    ] = None,
    # POST-PROCESS
    convert: Annotated[
        RichAVContainer | None,
        Parameter(
            help="Remux or recode the downloaded file into a specific container.",
            short_alias=True,
            show_default=False,
            group=Panel.POST_PROCESS,
        ),
    ] = None,
    subtitles: Annotated[
        str | None,
        Parameter(
            help="Languages of subtitles to embed (e.g. [green]en[/] and [green]es[/]).",
            short_alias=True,
            group=Panel.POST_PROCESS,
        ),
    ] = None,
    embed_metadata: Annotated[
        bool,
        Parameter(
            negative="--no-metadata",
            help="Embed title, chapters, and thumbnail into the file.",
            group=Panel.POST_PROCESS,
        ),
    ] = True,
    sponsorblock: Annotated[
        bool,
        Parameter(
            negative="--no-sponsorblock",
            help="Automatically remove sponsor segments and intros (YouTube only).",
            group=Panel.POST_PROCESS,
        ),
    ] = False,
    ffmpeg_path: Annotated[
        Path | None,
        Parameter(
            help="FFmpeg executable to use.",
            show_default=False,
            group=Panel.POST_PROCESS,
        ),
    ] = None,
    # SHARED
    auth: ExtractorOptions | None = None,
    display: DisplayOptions | None = None,
):
    """Download video/audio from [green]URL[/] or search [green]service[/]."""

    auth = auth or ExtractorOptions()
    display = display or DisplayOptions()

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from remora import DownloadOptions, Remora
        from remora._internal.ffmpeg import get_ffmpeg
        from remora.exceptions import FFmpegNotFoundError, OutputTemplateError
        from remora.models.media import Playlist, SearchList
        from remora_cli.ui.download_handler import ProgressCallback
        from remora_cli.ui.extractor import extract_queries

        try:
            ffmpeg_path = get_ffmpeg(ffmpeg_path)
        except FFmpegNotFoundError:
            ffmpeg_path = None
            logger.warning("FFmpeg binary not found, post-processing disabled")

        try:
            config = DownloadOptions(
                output_template=output,
                skip_existing=skip_existing,
                format_type=type,
                convert_to=convert,
                quality=quality,
                ffmpeg_path=ffmpeg_path,
                max_workers=max_workers,
                embed_metadata=embed_metadata,
            )
        except OutputTemplateError as error:
            raise CycloptsError(str(error))

        remora = Remora(download_options=config)

    async for target, result in extract_queries(query, remora.extractor):
        if isinstance(result, (Playlist, SearchList)) and not result.entries.medias():
            logger.error("'{}' don't have streams to download", target)

        if isinstance(result, SearchList):
            result = result.entries.medias()[0]

        async with ProgressCallback(display.quiet) as progress:
            async for event in remora.download_batch(result):
                await progress.playlist_callback(event)
