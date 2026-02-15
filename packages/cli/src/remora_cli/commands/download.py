from enum import Enum
from pathlib import Path
from typing import Annotated

from loguru import logger
from remora.downloader.config import DEFAULT_OUTPUT_TEMPLATE
from remora.types import FILE_FORMAT
from remora_cli.completions import complete_output, complete_query, complete_resolution
from remora_cli.config import CONFIG
from remora_cli.helpers import make_async

from remora_cli.ui.rich import Status
from typer import Argument, BadParameter, Option, Typer


class HelpPanel(str, Enum):
    file = "File"
    downloader = "Downloader"


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
        FILE_FORMAT,
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
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.file,
            autocompletion=complete_output,
            show_default=False,
            dir_okay=True,
            file_okay=False,
        ),
    ] = DEFAULT_OUTPUT_TEMPLATE,
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

    # Lazy Import
    with Status("Starting[blink]...[/]"):
        from remora.downloader.main import MediaDownloader
        from remora.extractor import MediaExtractor
        from remora_cli.ui.progress import ProgressCallback
        from remora_cli.ui.extractor import extract_queries

    # Initialize
    try:
        extractor = MediaExtractor(use_cache=CONFIG.cache)
        downloader = MediaDownloader(
            format=format,
            quality=quality,
            output=output,
            max_workers=max_workers,
            ffmpeg_path=ffmpeg_path,
            extractor=extractor,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    if downloader.config.convert and not downloader.config.ffmpeg_path:
        logger.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    async for result in extract_queries(query, extractor):
        async with ProgressCallback(CONFIG.quiet) as progress:
            async for event in downloader.download_batch(result):
                await progress.playlist_callback(event)
