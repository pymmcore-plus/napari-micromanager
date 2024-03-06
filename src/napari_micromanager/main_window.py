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
from pymmcore_widgets import ConfigWizard

from ._core_link import CoreViewerLink
from ._gui_objects._startup_widget import NEW, StartupDialog
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:
    from pathlib import Path

    from pymmcore_plus.core.events._protocol import PSignalInstance


# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)
logging.getLogger("in_n_out").setLevel(logging.WARNING)


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self, viewer: napari.viewer.Viewer, config: str | Path | None = None
    ) -> None:
        super().__init__(viewer)

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

        # if a config is passed, load it
        self._handle_system_configuration(config)

    def _handle_system_configuration(self, config: str | Path | None) -> None:
        """Handle the system configuration file. If None, show the startup dialog."""
        startup = StartupDialog(self.viewer.window._qt_window)

        if config is not None:
            self._load_system_configuration(config)
            # add the path to the json file
            startup.add_path_to_json(config)
            return

        # if no config is passed, show the startup dialog
        self._center_startup_dialog()
        if startup.exec_():
            config = startup.value()
            # if the user selected NEW, show the config wizard
            if config == NEW:
                # TODO: subclass to load the new cfg if created and to add it to the
                # json file. instead of show() should use exec_() and check the return
                self._cfg_wizard = ConfigWizard(parent=self.viewer.window._qt_window)
                self._cfg_wizard.show()
            else:
                self._load_system_configuration(config)

    def _load_system_configuration(self, config: str | Path) -> None:
        """Load a Micro-Manager system configuration file."""
        try:
            self._mmc.loadSystemConfiguration(config)
        except FileNotFoundError:
            # don't crash if the user passed an invalid config
            warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

    def _center_startup_dialog(self) -> None:
        """Center the startup dialog in the viewer window."""
        self._startup.move(
            self.viewer.window.qt_viewer.geometry().center()
            - self._startup.geometry().center()
        )
        self._startup.resize(
            int(self.viewer.window.qt_viewer.geometry().width() / 2),
            self._startup.sizeHint().height(),
        )

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
