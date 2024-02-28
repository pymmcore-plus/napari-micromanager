from __future__ import annotations

import atexit
import base64
import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from warnings import warn

import appdirs
import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QByteArray
from qtpy.QtWidgets import QDockWidget

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import DOCK_WIDGETS, MicroManagerToolbar

if TYPE_CHECKING:

    from pymmcore_plus.core.events._protocol import PSignalInstance
    from qtpy.QtGui import QCloseEvent

# Path to the user data directory to store the layout
USER_DATA_DIR = Path(appdirs.user_data_dir(appname="napari_micromanager"))
USER_LAYOUT_PATH = USER_DATA_DIR / "napari_micromanager_layout.json"

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
        self.viewer.window._qt_window.closeEvent = self._close_event

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

        # load layout
        self._load_layout()

        # load config file
        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

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
        """Save the napa-micromanager layout to a json file.

        The json file has two keys:
        - "layout_state" where the state of napari main window is stored using the
          saveState() method. The state is base64 encoded to be able to save it to the
          json file.
        - "pymmcore_widgets" where the names of the docked pymmcore_widgets are stored.

        IMPORTANT: The "pymmcore_widgets" key is crucial in our layout saving process.
        It stores the names of all active pymmcore_widgets at the time of saving. Before
        restoring the layout, we must recreate these widgets. If not, they won't be
        included in the restored layout.
        """
        # get the names of the pymmcore_widgets that are part of the layout
        pymmcore_wdgs: list[str] = []
        main_win = self.viewer.window._qt_window
        for dock_wdg in main_win.findChildren(QDockWidget):
            wdg_name = dock_wdg.objectName()
            if wdg_name in DOCK_WIDGETS:
                pymmcore_wdgs.append(wdg_name)

        # get the state of the napari main window as bytes
        state_bytes = self.viewer.window._qt_window.saveState().data()

        # Create dictionary with widget names and layout state. The layout state is
        # base64 encoded to be able to save it to a json file.
        data = {
            "pymmcore_widgets": pymmcore_wdgs,
            "layout_state": base64.b64encode(state_bytes).decode(),
        }

        # if the user layout path does not exist, create it
        if not USER_LAYOUT_PATH.exists():
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with open(USER_LAYOUT_PATH, "w") as json_file:
                json.dump(data, json_file)
        except Exception as e:
            print(f"Was not able to save layout to file. Error: {e}")

    def _load_layout(self) -> None:
        """Load the napari-micromanager layout from a json file."""
        if not USER_LAYOUT_PATH.exists():
            return

        try:
            with open(USER_LAYOUT_PATH) as f:
                data = json.load(f)

                # get the layout state bytes
                state_bytes = data.get("layout_state")

                if state_bytes is None:
                    return

                # add pymmcore_widgets to the main window
                pymmcore_wdgs = data.get("pymmcore_widgets", [])
                for wdg_name in pymmcore_wdgs:
                    if wdg_name in DOCK_WIDGETS:
                        self._show_dock_widget(wdg_name)

                # Convert base64 encoded string back to bytes
                state_bytes = base64.b64decode(state_bytes)

                # restore the layout state
                self.viewer.window._qt_window.restoreState(QByteArray(state_bytes))

        except Exception as e:
            print(f"Was not able to load layout from file. Error: {e}")

    def _close_event(self, event: QCloseEvent | None) -> None:
        """Close the napari-micromanager plugin and save the layout."""
        self._save_layout()
        self._napari_close_event(event)
