from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Annotated

import anyio
from loguru import logger
from remora.downloader.config import DEFAULT_OUTPUT_TEMPLATE
from remora.types import FILE_FORMAT
from typer import Argument, BadParameter, Exit, Option, Typer

from remora_cli.completions import (
    complete_output,
    complete_query,
    complete_resolution,
    parse_queries,
)
from remora_cli.config import CONFIG
from remora_cli.ui.rich import Status


class HelpPanel(str, Enum):
    file = "File"
    downloader = "Downloader"


app = Typer()


def make_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from functools import partial

        return anyio.run(partial(func, *args, **kwargs))

    return wrapper


@app.command(no_args_is_help=True)
@make_async
async def download(
    query: Annotated[
        list[str],
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download [grey62](Default)[/].\n
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
            - To get BEST, select [green]video[/] or [green]audio[/] [grey62](Fast)[/].\n
            - To convert, select a file [green]EXTENSION[/] [grey62](Slow)[/].
            """,
            metavar="TYPE | EXTENSION",
            prompt="""
What format you want request?

- To get BEST, select 'video' or 'audio' (Fast).
- To convert, select a file EXTENSION (Slow).

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
    threads: Annotated[
        int,
        Option(
            "--threads",
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
    cache: Annotated[
        bool,
        Option(help="Process without use the cache."),
    ] = True,
):
    """Download video/audio from [green]URL[/] or search [green]SERVICE[/]."""

    # Lazy Import
    with Status("Starting[blink]...[/]"):
        from remora.downloader.main import MediaDownloader
        from remora.exceptions import MediaError
        from remora.extractor import MediaExtractor

        from remora_cli.ui.callback import ProgressCallback

    # Initialize
    progress = ProgressCallback()
    on_progress = None
    on_playlist = None

    if not CONFIG.quiet:
        on_progress = progress.callback_media
        on_playlist = progress.callback_playlist

    try:
        extractor = MediaExtractor(use_cache=cache)
        downloader = MediaDownloader(
            format=format,
            quality=quality,
            output=output,
            threads=threads,
            ffmpeg_path=ffmpeg_path,
            extractor=extractor,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    if downloader.config.convert and not downloader.config.ffmpeg_path:
        logger.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    for target, entry in parse_queries(query):
        try:
            with Status("Searching[blink]...[/]"):
                if target == "url":
                    logger.info('🔎 Extract URL: "{url}".', url=entry)
                    result = await extractor.extract_url(entry)

                    if result.type == "playlist":
                        logger.info('🔎 Playlist title: "{title}".', title=result.title)

                        if not result.medias and result.playlists:
                            logger.warning(
                                "❗ The URL only have multiple playlists but no medias, please try again with a single playlist."
                            )
                            raise Exit()
                else:
                    logger.info(
                        '🔎 Search from {extractor}: "{query}".',
                        extractor=target,
                        query=entry,
                    )

                    result = await extractor.extract_search(entry, target)

                    if not result.medias:
                        logger.warning("❗ No results found.")
                        raise Exit()

                    result = result.medias[0]

            await downloader.download_all(result, on_progress, on_playlist)
            logger.info("✅ Download Finished.")
        except MediaError as err:
            logger.error("❌ {error}", error=str(err))
        finally:
            logger.info("")
