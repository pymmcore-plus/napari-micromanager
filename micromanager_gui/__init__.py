try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from .main_window import MainWindow

__all__ = [
    "__version__",
    "MainWindow",
]
