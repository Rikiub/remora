from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, CycloptsError, Parameter
from loguru import logger

from remora.models.container.extension.audio import SafeAudioExtensionStr
from remora.models.container.extension.video import SafeVideoExtensionStr
from remora.models.container.format import FormatType
from remora.types import DEFAULT_TEMPLATE
from remora_cli.config import CONFIG
from remora_cli.helpers import unwrap_literals
from remora_cli.ui.rich import CONSOLE


class HelpPanel(StrEnum):
    FILTERS = "Filters"
    DOWNLOADER = "Downloader"
    POST_PROCESS = "Post-processing"
    AUTH = "Authentication"


FormatEnum = StrEnum("FormatEnum", {s: s for s in unwrap_literals(FormatType)})

ExtensionEnum = StrEnum(
    "ExtensionEnum",
    {s: s for s in unwrap_literals(Literal[SafeVideoExtensionStr, SafeAudioExtensionStr])},
)

app = App(
    name="download",
    help="Download video/audio from [green]URL[/] or search [green]service[/].",
)


@app.command
async def download(
    # ARGUMENTS
    query: Annotated[
        list[str],
        Parameter(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download. [grey62](Default)[/]\n
            - Insert a [green]service[/]:[green]query[/] to search and download.
            """,
            show_default=False,
        ),
    ],
    # OPTIONS
    output: Annotated[
        str,
        Parameter(
            name=["--output", "-o"],
            help="Path or template for the saved file.",
            show_default=True,
        ),
    ] = DEFAULT_TEMPLATE,
    interactive: Annotated[
        bool,
        Parameter(
            name="--interactive",
            negative="--no-interactive",
            help="Interactively select streams or playlist items.",
        ),
    ] = True,
    # FILTER
    type: Annotated[
        FormatEnum,  # type: ignore
        Parameter(
            name=["--type", "-t"],
            help="Type of stream to download (downloads best format by default).",
            show_default=False,
            group=HelpPanel.FILTERS,
        ),
    ] = FormatEnum.video,  # type: ignore
    quality: Annotated[
        int | None,
        Parameter(
            name=["--quality", "-q"],
            help="Prefered target quality.",
            group=HelpPanel.FILTERS,
        ),
    ] = None,
    video_codec: Annotated[
        str | None,
        Parameter(
            name=["--video-codec", "--vcodec"],
            help="Prefered video codec.",
            group=HelpPanel.FILTERS,
        ),
    ] = None,
    audio_codec: Annotated[
        str | None,
        Parameter(
            name=["--audio-codec", "--acodec"],
            help="Prefered audio codec.",
            group=HelpPanel.FILTERS,
        ),
    ] = None,
    # DOWNLOADER
    skip_duplicates: Annotated[
        bool,
        Parameter(
            name="--skip-duplicates",
            negative="--force",
            help="Skip downloading if a file with the same name already exists, regardless of extension.",
            group=HelpPanel.DOWNLOADER,
        ),
    ] = True,
    max_workers: Annotated[
        int,
        Parameter(
            help="Limit of simultaneous downloads.",
            group=HelpPanel.DOWNLOADER,
        ),
    ] = 5,
    limit_rate: Annotated[
        str | None,
        Parameter(
            name="--limit-rate",
            help='Maximum download rate (e.g. [green]"5M"[/] or [green]"500K"[/]).',
            group=HelpPanel.DOWNLOADER,
        ),
    ] = None,
    # POST_PROCESS
    convert: Annotated[
        ExtensionEnum | None,  # type: ignore
        Parameter(
            name=["--convert", "-c"],
            help="Convert or remux the downloaded file into a specific extension.",
            show_default=False,
            group=HelpPanel.POST_PROCESS,
        ),
    ] = None,
    subtitles: Annotated[
        str | None,
        Parameter(
            name=["--subtitles", "-s"],
            help='Languages of subtitles to embed (e.g. [green]"en,es"[/] or [green]"all"[/]).',
            group=HelpPanel.POST_PROCESS,
        ),
    ] = "all",
    embed_metadata: Annotated[
        bool,
        Parameter(
            name="--embed-metadata",
            negative="--no-metadata",
            help="Embed title, chapters, and thumbnail into the file.",
            group=HelpPanel.POST_PROCESS,
        ),
    ] = True,
    sponsorblock: Annotated[
        bool,
        Parameter(
            name="--sponsorblock",
            negative="--no-sponsorblock",
            help="Automatically remove sponsor segments and intros (YouTube only).",
            group=HelpPanel.POST_PROCESS,
        ),
    ] = False,
    ffmpeg_path: Annotated[
        Path | None,
        Parameter(
            name="--ffmpeg-path",
            help="FFmpeg executable to use.",
            show_default=False,
            group=HelpPanel.POST_PROCESS,
        ),
    ] = None,
    # AUTH
    cookies: Annotated[
        str | None,
        Parameter(
            help="Browser name or path to a [green]cookies.txt[/] file.",
            group=HelpPanel.AUTH,
        ),
    ] = None,
    proxy: Annotated[
        str | None,
        Parameter(
            name="--proxy",
            help="HTTP/HTTPS/SOCKS5 proxy [green]URL[/].",
            group=HelpPanel.AUTH,
        ),
    ] = None,
):
    """Download video/audio from URL or search service."""

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
                format_type=type,  # type: ignore
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

        async with ProgressCallback(CONFIG.quiet) as progress:
            async for event in remora.download_batch(result):
                await progress.playlist_callback(event)