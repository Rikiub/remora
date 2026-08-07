from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from loguru import logger
from typer import Argument, BadParameter, Option, Typer

from remora.models.container.extension.audio import SafeAudioExtensionStr
from remora.models.container.extension.video import SafeVideoExtensionStr
from remora.models.container.format import FormatType
from remora.types import DEFAULT_TEMPLATE
from remora_cli.completions import complete_output, complete_query, complete_resolution
from remora_cli.config import CONFIG
from remora_cli.helpers import make_async, unwrap_literals
from remora_cli.ui.rich import CONSOLE


class HelpPanel(StrEnum):
    FILTERS = "Filters"
    DOWNLOADER = "Downloader"
    POST_PROCESS = "Post-processing"
    AUTH = "Authentication"


FormatEnum = unwrap_literals(FormatType)
FormatEnum = StrEnum("FormatEnum", {s: s for s in FormatEnum})

ExtensionEnum = unwrap_literals(Literal[SafeVideoExtensionStr, SafeAudioExtensionStr])
ExtensionEnum = StrEnum("ExtensionEnum", {s: s for s in ExtensionEnum})

app = Typer()


@app.command(no_args_is_help=True)
@make_async
async def download(
    # ARGUMENTS
    query: Annotated[
        list[str],
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download. [grey62](Default)[/]\n
            - Insert a [green]service[/]:[green]query[/] to search and download.
            """,
            show_default=False,
            autocompletion=complete_query,
        ),
    ],
    # OPTIONS
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            help="Path or template for the saved file.",
            autocompletion=complete_output,
            show_default=True,
        ),
    ] = DEFAULT_TEMPLATE,
    interactive: Annotated[
        bool,
        Option(
            "--interactive/--no-interactive",
            help="Interactively select streams or playlist items.",
        ),
    ] = True,
    # FILTER
    type: Annotated[
        FormatEnum,  # type: ignore
        Option(
            "--type",
            "-t",
            help="Type of stream to download (downloads best format by default).",
            show_default=False,
            rich_help_panel=HelpPanel.FILTERS,
        ),
    ] = FormatEnum.video,  # type: ignore
    quality: Annotated[
        int | None,
        Option(
            "--quality",
            "-q",
            help="Prefered target quality.",
            rich_help_panel=HelpPanel.FILTERS,
            autocompletion=complete_resolution,
        ),
    ] = None,
    video_codec: Annotated[
        str | None,
        Option(
            "--video-codec/--vcodec",
            help="Prefered video codec.",
            rich_help_panel=HelpPanel.FILTERS,
        ),
    ] = None,
    audio_codec: Annotated[
        str | None,
        Option(
            "--audio-codec/--acodec",
            help="Prefered audio codec.",
            rich_help_panel=HelpPanel.FILTERS,
        ),
    ] = None,
    # DOWNLOADER
    skip_duplicates: Annotated[
        bool,
        Option(
            "--skip-duplicates/--force",
            help="Skip downloading if a file with the same name already exists, regardless of extension.",
            rich_help_panel=HelpPanel.DOWNLOADER,
        ),
    ] = True,
    max_workers: Annotated[
        int,
        Option(
            help="Limit of simultaneous downloads.",
            rich_help_panel=HelpPanel.DOWNLOADER,
        ),
    ] = 5,
    limit_rate: Annotated[
        str | None,
        Option(
            "--limit-rate",
            help='Maximum download rate (e.g. [green]"5M"[/] or [green]"500K"[/]).',
            rich_help_panel=HelpPanel.DOWNLOADER,
        ),
    ] = None,
    # POST_PROCESS
    convert: Annotated[
        ExtensionEnum | None,  # type: ignore
        Option(
            "--convert",
            "-c",
            help="Convert or remux the downloaded file into a specific extension.",
            show_default=False,
            rich_help_panel=HelpPanel.POST_PROCESS,
        ),
    ] = None,
    subtitles: Annotated[
        str | None,
        Option(
            "--subtitles",
            "-s",
            help='Languages of subtitles to embed (e.g. [green]"en,es"[/] or [green]"all"[/]).',
            rich_help_panel=HelpPanel.POST_PROCESS,
        ),
    ] = "all",
    embed_metadata: Annotated[
        bool,
        Option(
            "--embed-metadata/--no-metadata",
            help="Embed title, chapters, and thumbnail into the file.",
            rich_help_panel=HelpPanel.POST_PROCESS,
        ),
    ] = True,
    sponsorblock: Annotated[
        bool,
        Option(
            "--sponsorblock/--no-sponsorblock",
            help="Automatically remove sponsor segments and intros (YouTube only).",
            rich_help_panel=HelpPanel.POST_PROCESS,
        ),
    ] = False,
    ffmpeg_path: Annotated[
        Path | None,
        Option(
            help="FFmpeg executable to use.",
            rich_help_panel=HelpPanel.POST_PROCESS,
            show_default=False,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    # AUTH
    cookies: Annotated[
        str | None,
        Option(
            help="Browser name or path to a [green]cookies.txt[/] file.",
            rich_help_panel=HelpPanel.AUTH,
            metavar="<chrome|firefox|brave|edge|file>",
            file_okay=True,
        ),
    ] = None,
    proxy: Annotated[
        str | None,
        Option(
            "--proxy",
            help="HTTP/HTTPS/SOCKS5 proxy [green]URL[/].",
            rich_help_panel=HelpPanel.AUTH,
            metavar="<url>",
        ),
    ] = None,
):
    """Download video/audio from [green]URL[/] or search [green]service[/]."""

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
            raise BadParameter(str(error))

        remora = Remora(download_options=config)

    async for target, result in extract_queries(query, remora.extractor):
        if isinstance(result, (Playlist, SearchList)) and not result.entries.medias():
            logger.error("'{}' don't have streams to download", target)

        if isinstance(result, SearchList):
            result = result.entries.medias()[0]

        async with ProgressCallback(CONFIG.quiet) as progress:
            async for event in remora.download_batch(result):
                await progress.playlist_callback(event)
