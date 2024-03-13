from __future__ import annotations

import atexit
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Callable, cast

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets.hcwizard.intro_page import SRC_CONFIG
from qtpy.QtWidgets import QAction, QMenuBar

from napari_micromanager._util import (
    load_sys_config,
    save_sys_config_dialog,
)

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import MicroManagerToolbar
from ._init_system_configs import HardwareConfigWizard, InitializeSystemConfigurations

if TYPE_CHECKING:
    from pathlib import Path

    from pymmcore_plus.core.events._protocol import PSignalInstance


# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)
logging.getLogger("in_n_out").setLevel(logging.WARNING)


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        config: str | Path | None = None,
        *,
        init_configs: bool = True,
    ) -> None:
        super().__init__(viewer)

        self._add_menu()

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

        # Micro-Manager Hardware Configuration Wizard
        self._wiz: HardwareConfigWizard | None = None

        if init_configs:
            # handle the system configurations at startup. with this we create/update
            # the list of the Micro-Manager hardware system configurations files path
            # stored as a json file in the user's configuration file directory
            # (USER_CONFIGS_PATHS).
            # a dialog will be also displayed if no system configuration file is
            # provided to either select one from the list of available ones or to create
            # a new one.
            self._init_cfg = InitializeSystemConfigurations(
                parent=self.viewer.window._qt_window, config=config, mmcore=self._mmc
            )
            return

        if config:
            load_sys_config(config)

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

    def _add_menu(self) -> None:
        if (win := getattr(self.viewer.window, "_qt_window", None)) is None:
            return

        menubar = cast(QMenuBar, win.menuBar())

        # main Micro-Manager menu
        mm_menu = menubar.addMenu("Micro-Manager")

        # Configurations Sub-Menu
        configurations_menu = mm_menu.addMenu("System Configurations")
        # save cfg
        self.act_save_configuration = QAction("Save Configuration", self)
        self.act_save_configuration.triggered.connect(self._save_cfg)
        configurations_menu.addAction(self.act_save_configuration)
        # load cfg
        self.act_load_configuration = QAction("Load Configuration", self)
        self.act_load_configuration.triggered.connect(self._load_cfg)
        configurations_menu.addAction(self.act_load_configuration)
        # cfg wizard
        self.act_cfg_wizard = QAction("Hardware Configuration Wizard", self)
        self.act_cfg_wizard.triggered.connect(self._show_config_wizard)
        configurations_menu.addAction(self.act_cfg_wizard)

    def _save_cfg(self) -> None:
        """Save the current Micro-Manager system configuration."""
        save_sys_config_dialog(parent=self.viewer.window._qt_window, mmcore=self._mmc)

    def _load_cfg(self) -> None:
        """Load a Micro-Manager system configuration."""
        # load_sys_config_dialog(parent=self.viewer.window._qt_window, mmcore=self._mmc)
        InitializeSystemConfigurations(
            parent=self.viewer.window._qt_window, mmcore=self._mmc
        )

    def _show_config_wizard(self) -> None:
        """Show the Micro-Manager Hardware Configuration Wizard."""
        if self._wiz is None:
            self._wiz = HardwareConfigWizard(parent=self.viewer.window._qt_window)

        if self._wiz.isVisible():
            self._wiz.raise_()
        else:
            current_cfg = self._mmc.systemConfigurationFile() or ""
            self._wiz.setField(SRC_CONFIG, current_cfg)
            self._wiz.show()
