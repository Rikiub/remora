from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, CycloptsError, Parameter
from loguru import logger

from remora.models.container.extension.audio import SafeAudioExtensionStr
from remora.models.container.extension.video import SafeVideoExtensionStr
from remora.models.container.format import FormatType
from remora.types import DEFAULT_TEMPLATE, VideoQuality
from remora_cli.options import AuthOptions, DisplayOptions, QueryParameter
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
    /,
    # OPTIONS
    output: Annotated[
        str,
        Parameter(
            help="Path or template for the saved file.",
            short_alias=True,
            show_default=True,
        ),
    ] = DEFAULT_TEMPLATE,
    interactive: Annotated[
        bool,
        Parameter(
            help="Interactively select streams or playlist items.",
        ),
    ] = True,
    # FILTER
    type: Annotated[
        FormatType,
        Parameter(
            help="Type of stream to download (downloads best format by default).",
            short_alias=True,
            show_default=False,
            group=Panel.FILTERS,
        ),
    ] = "video",
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
            name=["--video-codec", "--vcodec"],
            help="Prefered video codec.",
            group=Panel.FILTERS,
        ),
    ] = None,
    audio_codec: Annotated[
        str | None,
        Parameter(
            name=["--audio-codec", "--acodec"],
            help="Prefered audio codec.",
            group=Panel.FILTERS,
        ),
    ] = None,
    # DOWNLOADER
    skip_duplicates: Annotated[
        bool,
        Parameter(
            negative="--force",
            help="Skip downloading if a file with the same name already exists, regardless of extension.",
            group=Panel.DOWNLOADER,
        ),
    ] = True,
    max_workers: Annotated[
        int,
        Parameter(
            help="Limit of simultaneous downloads.",
            group=Panel.DOWNLOADER,
        ),
    ] = 5,
    limit_rate: Annotated[
        str | None,
        Parameter(
            name="--limit-rate",
            help="Maximum download rate (e.g. [green]5M[/] or [green]500K[/]).",
            group=Panel.DOWNLOADER,
        ),
    ] = None,
    # POST-PROCESS
    convert: Annotated[
        Literal[SafeVideoExtensionStr, SafeAudioExtensionStr] | None,
        Parameter(
            help="Convert or remux the downloaded file into a specific extension.",
            short_alias=True,
            show_default=False,
            group=Panel.POST_PROCESS,
        ),
    ] = None,
    subtitles: Annotated[
        str | None,
        Parameter(
            help="Languages of subtitles to embed (e.g. [green]en,es[/] or [green]all[/]).",
            short_alias=True,
            group=Panel.POST_PROCESS,
        ),
    ] = "all",
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
    auth: AuthOptions | None = None,
    display: DisplayOptions | None = None,
):
    """Download video/audio from URL or search service."""

    auth = auth or AuthOptions()
    display = display or DisplayOptions()

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from remora import DownloadOptions, Remora
        from remora._internal.ffmpeg import get_ffmpeg
        from remora.exceptions import FFmpegNotFoundError, OutputTemplateError
        from remora.models.media.list import Playlist, SearchList
        from remora_cli.ui.extractor import extract_queries
        from remora_cli.ui.progress import ProgressCallback

        try:
            ffmpeg_path = get_ffmpeg(ffmpeg_path)
        except FFmpegNotFoundError:
            ffmpeg_path = None
            logger.warning("FFmpeg binary not found, post-processing disabled")

        try:
            config = DownloadOptions(
                output_template=output,
                format_type=type,
                convert_to=convert,
                quality=quality,
                ffmpeg_path=ffmpeg_path,
                max_workers=max_workers,
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
