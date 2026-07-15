from enum import StrEnum
from pathlib import Path
from typing import Annotated, get_args

from click import Choice
from loguru import logger
from typer import Argument, BadParameter, Option, Typer

from remora.models.format.audio import SafeAudioExtensionStr
from remora.models.format.type import FormatKindStr
from remora.models.format.video import SafeVideoExtensionStr
from remora.types import DEFAULT_TEMPLATE
from remora_cli.completions import complete_output, complete_query, complete_resolution
from remora_cli.config import CONFIG
from remora_cli.helpers import make_async
from remora_cli.ui.rich import CONSOLE


class HelpPanel(StrEnum):
    file = "File"
    downloader = "Downloader"


FORMAT_CHOICES = [
    s
    for lit in (FormatKindStr, SafeVideoExtensionStr, SafeAudioExtensionStr)
    for s in get_args(lit)
]

app = Typer()


@app.command(no_args_is_help=True)
@make_async
async def download(
    query: Annotated[
        list[str],
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download. [grey62](Default)[/]\n
            - Select a [green]SERVICE[/] to search and download.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar="URL | SERVICE",
        ),
    ],
    format: Annotated[
        str,
        Option(
            "--format",
            "-f",
            help="""File type to request.\n
            - To get BEST, select [green]video[/] or [green]audio[/]. [grey62](Fast)[/]\n
            - To convert, select a file [green]EXTENSION[/]. [grey62](Slow)[/]
            """,
            metavar="TYPE | EXTENSION",
            prompt="""
What format you want request?

- To get BEST, select 'video' or 'audio' (Fast)
- To convert, select a file EXTENSION (Slow)

""",
            prompt_required=False,
            show_default=False,
            rich_help_panel=HelpPanel.file,
            click_type=Choice(FORMAT_CHOICES),
        ),
    ] = "video",
    quality: Annotated[
        int | None,
        Option(
            "--quality",
            "-q",
            help="Prefered video/audio quality to filter.",
            rich_help_panel=HelpPanel.file,
            autocompletion=complete_resolution,
            show_default=False,
        ),
    ] = None,
    output: Annotated[
        str,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.file,
            autocompletion=complete_output,
            show_default=False,
        ),
    ] = DEFAULT_TEMPLATE,
    max_workers: Annotated[
        int,
        Option(
            help="Limit of simultaneous downloads.",
            rich_help_panel=HelpPanel.downloader,
        ),
    ] = 5,
    ffmpeg_path: Annotated[
        Path | None,
        Option(
            help="FFmpeg executable to use.",
            rich_help_panel=HelpPanel.downloader,
            show_default=False,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
):
    """Download video/audio from [green]URL[/] or search [green]SERVICE[/]."""

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from remora import DownloadOptions, Remora
        from remora.exceptions import OutputTemplateError
        from remora.models.media.list import Playlist, SearchList
        from remora_cli.ui.extractor import extract_queries
        from remora_cli.ui.progress import ProgressCallback

        try:
            config = DownloadOptions(
                output_template=output,
                format=format,  # type: ignore
                quality=quality,
                ffmpeg_path=ffmpeg_path,
                max_workers=max_workers,
            )
        except OutputTemplateError as error:
            raise BadParameter(str(error))

        remora = Remora(download_options=config)

    async for target, result in extract_queries(query, remora._extractor):
        if isinstance(result, (Playlist, SearchList)):
            if not result.medias:
                logger.error("'{}' don't have streams to download", target)

        if isinstance(result, SearchList):
            result = result.medias[0]

        async with ProgressCallback(CONFIG.quiet) as progress:
            async for event in remora.download_batch(result):
                await progress.playlist_callback(event)
