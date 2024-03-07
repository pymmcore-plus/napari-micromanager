from __future__ import annotations

import atexit
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Callable

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import MicroManagerToolbar
from ._init_system_configs import InitializeSystemConfigurations

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

        # handle the system configurations at startup. with this we create/update the
        # list of the Micro-Manager hardware system configurations files path stored as
        # a json file in the user's configuration file directory (USER_CONFIGS_PATHS).
        # a dialog will be also displayed if no system configuration file is provided
        # to either select one from the list of available ones or to create a new one.
        self._init_cfg = InitializeSystemConfigurations(
            parent=self.viewer.window._qt_window, config=config, mmcore=self._mmc
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
