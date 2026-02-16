from enum import Enum, StrEnum
from pathlib import Path
from typing import Annotated

from loguru import logger
from remora.helpers import literal_to_set
from remora.models.download_options import DEFAULT_OUTPUT_TEMPLATE
from remora.types import StreamTarget
from remora_cli.completions import complete_output, complete_query, complete_resolution
from remora_cli.config import CONFIG
from remora_cli.helpers import make_async
from remora_cli.ui.rich import Status
from typer import Argument, BadParameter, Option, Typer


class HelpPanel(str, Enum):
    file = "File"
    downloader = "Downloader"


FormatEnum = StrEnum("FormatEnum", {v.upper(): v for v in literal_to_set(StreamTarget)})

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
        FormatEnum,  # type: ignore
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
        from remora import DownloadOptions, MediaExtractor, RemoraAPI
        from remora_cli.ui.extractor import extract_queries
        from remora_cli.ui.progress import ProgressCallback

    # Initialize
    try:
        config = DownloadOptions(
            format=format,
            quality=quality,
            template=output,
            max_workers=max_workers,
            ffmpeg_path=ffmpeg_path,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    api = RemoraAPI(
        download_config=config,
        extractor=MediaExtractor(use_cache=CONFIG.cache),
    )

    if config.convert and not config.ffmpeg_path:
        logger.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    async for result in extract_queries(query, api.extractor):
        async with ProgressCallback(CONFIG.quiet) as progress:
            async for event in api.download_batch(result):
                await progress.playlist_callback(event)
