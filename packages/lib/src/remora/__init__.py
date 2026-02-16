"""Remora API. Handler for URLs extraction, serialization and medias download."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .__init__imports import *  # noqa: F403
else:
    from lazy_imports import LazyModule, as_package, load, module_source

    load(
        LazyModule(
            *as_package(__file__),
            module_source(".__init__imports", __name__),
            name=__name__,
            doc=__doc__,
        )
    )
