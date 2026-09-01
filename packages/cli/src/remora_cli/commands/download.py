from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter, validators
from loguru import logger

from remora.constants import DEFAULT_TEMPLATE, DEFAULT_WORKERS
from remora.exceptions import FFmpegNotFoundError
from remora.ffmpeg import get_ffmpeg_dir, validate_ffmpeg_dir
from remora.models import (
    AudioCodec,
    AVContainerFormat,
    DownloadOptions,
    Playlist,
    RichAVContainer,
    SearchList,
    VideoCodec,
)
from remora.template import validate_template
from remora_cli.options import (
    DisplayOptions,
    NetworkOptions,
    QueryParameter,
)
from remora_cli.ui.download_handler import ProgressCallback
from remora_cli.ui.rich import CONSOLE


class Panel(StrEnum):
    FILTERS = "Filter"
    DOWNLOADER = "Download"
    POST_PROCESS = "Post-process"


FormatQuality = Literal[144, 240, 360, 480, 720, 1080]
app = App()


def _validate_ffmpeg(type_, value):
    if value:
        validators.Path(
            exists=True,
            file_okay=False,
            dir_okay=True,
        )(type_, value)
        validate_ffmpeg_dir(value)


@app.command
async def download(
    query: QueryParameter,
    *,
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
        int | FormatQuality | None,
        Parameter(
            help="Prefered target quality.",
            short_alias=True,
            group=Panel.FILTERS,
        ),
    ] = None,
    video_codec: Annotated[
        VideoCodec | str | None,
        Parameter(
            help="Prefered video codec.",
            alias="--vcodec",
            group=Panel.FILTERS,
        ),
    ] = None,
    audio_codec: Annotated[
        AudioCodec | str | None,
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
            validator=lambda type, v: validate_template(v),
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
    ffmpeg_location: Annotated[
        Path | None,
        Parameter(
            help="FFmpeg executable to use.",
            show_default=False,
            group=Panel.POST_PROCESS,
            validator=_validate_ffmpeg,
        ),
    ] = None,
    # SHARED
    network: NetworkOptions | None = None,
    display: DisplayOptions | None = None,
):
    """Download video/audio from [green]URL[/] or search [green]service[/]."""

    network = network or NetworkOptions()
    display = display or DisplayOptions()

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from remora import Remora
        from remora_cli.ui.extractor import extract_queries

        try:
            get_ffmpeg_dir(ffmpeg_location)
        except FFmpegNotFoundError:
            logger.warning(
                "FFmpeg binaries not found. Download quality could be degraded and post-processing will be disabled."
            )
            ffmpeg_location = None

        remora = Remora(
            download_options=DownloadOptions(
                output_template=output,
                skip_existing=skip_existing,
                format_type=type,
                convert_to=convert,
                quality=quality,
                ffmpeg_location=ffmpeg_location,
                max_workers=max_workers,
                embed_metadata=embed_metadata,
            ),
            network_options=network.build_options(),
        )

    async for target, result in extract_queries(query, remora.extractor):
        if isinstance(result, (Playlist, SearchList)) and not result.entries.medias():
            logger.error("'{}' don't have streams to download", target)

        if isinstance(result, SearchList):
            result = result.entries.medias()[0]

        async with (
            ProgressCallback(display.quiet) as wrapper,
            remora.download_batch(result) as progress,
        ):
            async for state in progress:
                await wrapper.playlist_callback(state)
