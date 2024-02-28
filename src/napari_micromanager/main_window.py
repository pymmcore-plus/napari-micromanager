from __future__ import annotations

import atexit
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Callable
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QByteArray

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:

    from pathlib import Path

    from pymmcore_plus.core.events._protocol import PSignalInstance
    from PyQt5.QtGui import QCloseEvent

PATH = "/Users/fdrgsp/Desktop/layout/layout.state"

# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self, viewer: napari.viewer.Viewer, config: str | Path | None = None
    ) -> None:
        super().__init__(viewer)

        # override the napari close event to save the layout
        self._napari_close_event = self.viewer.window._qt_window.closeEvent
        viewer.window._qt_window.closeEvent = self._close_event

        # get global CMMCorePlus instance
        self._mmc = CMMCorePlus.instance()
        # this object mediates the connection between the viewer and core events
        self._core_link = CoreViewerLink(viewer, self._mmc, self)

        # some remaining connections related to widgets ... TODO: unify with superclass
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self.viewer.layers.events, self._update_max_min),
            (self.viewer.layers.selection.events, self._update_max_min),
            (self.viewer.dims.events.current_step, self._update_max_min),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

        # add minmax dockwidget
        if "MinMax" not in getattr(self.viewer.window, "_dock_widgets", []):
            self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

        # load layout
        self._load_layout()

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._core_link.cleanup()
        atexit.unregister(self._cleanup)  # doesn't raise if not connected

    def _update_max_min(self, *_: Any) -> None:
        visible = (x for x in self.viewer.layers.selection if x.visible)
        self.minmax.update_from_layers(
            lr for lr in visible if isinstance(lr, napari.layers.Image)
        )

    def _save_layout(self) -> None:
        """Save the napa-micromanager layout to a file."""
        # Save the current state of the QMainWindow
        with open(PATH, "wb") as f:
            f.write(self.viewer.window._qt_window.saveState())

    def _load_layout(self) -> None:
        """Load the napari-micromanager layout from a file."""
        try:
            with open(PATH, "rb") as f:
                state = QByteArray(f.read())
                self.viewer.window._qt_window.restoreState(state)
        except FileNotFoundError:
            print("No saved state found.")

    def _close_event(self, event: QCloseEvent | None) -> None:
        """Close the napari-micromanager plugin and save the layout."""
        self._save_layout()
        self._napari_close_event(event)
