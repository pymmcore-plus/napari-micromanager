"""Napari-based GUI for MicroManager."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("napari-micromanager")
except PackageNotFoundError:
    __version__ = "uninstalled"

from .main_window import MainWindow

__all__ = ["__version__", "MainWindow"]
