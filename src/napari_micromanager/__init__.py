"""Napari-based GUI for MicroManager."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("napari-micromanager")
except PackageNotFoundError:
    __version__ = "uninstalled"


# ensure this gets imported before PyQt or other calls to os.add_dll_directory
# https://github.com/micro-manager/pymmcore/issues/119
import pymmcore  # noqa: F401

from .main_window import MainWindow

__all__ = ["__version__", "MainWindow"]
