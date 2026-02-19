"""Remora: data extractor and downloader."""

from typing import TYPE_CHECKING

from lazy_imports import LazyModule, as_package, load, module_source

if TYPE_CHECKING:
    from .__init__imports import *  # noqa: F403

load(
    LazyModule(
        *as_package(__file__),
        module_source(".__init__imports", __name__),
        name=__name__,
        doc=__doc__,
    )
)
