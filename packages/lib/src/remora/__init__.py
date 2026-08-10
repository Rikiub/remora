"""Remora: data extractor and downloader."""

import ast as _ast
from typing import TYPE_CHECKING as _TYPE_CHECKING

import lazy_imports as _lazy_imports

if _TYPE_CHECKING:
    """Remora public API imports."""
    from .__init__imports import *

_lazy_imports.load(
    module=_lazy_imports.LazyModule(
        *_lazy_imports.as_package(__file__),
        *(
            node
            for node in _ast.parse(_lazy_imports.module_source(".__init__imports", __name__)).body
            if isinstance(node, _ast.ImportFrom)
        ),
        name=__name__,
        doc=__doc__,
    )
)