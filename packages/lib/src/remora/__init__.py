"""Remora: data extractor and downloader."""

# Lazy import public API
import lazy_loader as _lazy

__getattr__, __dir__, __all__ = _lazy.attach_stub(__name__, __file__)

# Disable logging by default
import remora

remora.logs.disable()
