from __future__ import annotations

import atexit
import contextlib
import logging
import weakref
from typing import TYPE_CHECKING, Any
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus

from napari_micromanager._core_link import CoreViewerLink
from napari_micromanager._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pymmcore_plus.core.events._protocol import PSignalInstance


# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)
logging.getLogger("in_n_out").setLevel(logging.WARNING)


def get_main_window() -> MainWindow:
    """Return the MainWindow attached to the current napari viewer.

    Raises
    ------
    RuntimeError
        If no napari viewer or napari-micromanager MainWindow instance can be found.
    """
    viewer = napari.current_viewer()
    if viewer is None:
        raise RuntimeError("No active napari viewer found.")
    try:
        qt_window = viewer.window._qt_window
    except AttributeError:
        raise RuntimeError("Could not access napari Qt window.") from None
    win: MainWindow | None = qt_window.findChild(MainWindow)
    if win is None:
        raise RuntimeError("No napari-micromanager MainWindow in this viewer.")
    return win


def get_core() -> CMMCorePlus:
    """Return the CMMCorePlus instance used by the active MainWindow.

    Raises
    ------
    RuntimeError
        If no napari viewer or napari-micromanager MainWindow instance can be found.
    """
    return get_main_window().core


def _cfg_has_py_devices(path: str | Path) -> bool:
    """Return True if the cfg file contains ``#py`` device lines."""
    try:
        with open(path) as f:
            return any(line.strip().startswith("#py") for line in f)
    except (FileNotFoundError, OSError):
        return False


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        config: str | Path | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(viewer, mmcore=mmcore)
        self.set_core(self._mmc, owns=self._owns_core)

        # some remaining connections related to widgets ... TODO: unify with superclass
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self.viewer.layers.events, self._update_max_min),
            (self.viewer.layers.selection.events, self._update_max_min),
            (self.viewer.dims.events.current_step, self._update_max_min),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

        # add minmax dockwidget
        if "MinMax" not in getattr(self.viewer.window, "dock_widgets", []):
            self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

        # Weakref indirection: a bound-method callback here would make the
        # registration itself pin `self`, so `destroyed`/`atexit` never fire.
        self_ref = weakref.ref(self)

        def _weak_cleanup(*_: object) -> None:
            inst = self_ref()
            if inst is not None:
                inst._cleanup()

        self._weak_cleanup = _weak_cleanup

        # Proactive trigger: fires when the user closes the napari window,
        # while the viewer is still alive enough to disconnect signals.
        qt_window = getattr(self.viewer.window, "_qt_window", None)
        if qt_window is None:
            warn(
                "napari viewer has no `_qt_window`; eager cleanup on window "
                "close is disabled and device handles may leak until process "
                "exit.",
                stacklevel=2,
            )
        else:
            qt_window.destroyed.connect(_weak_cleanup)

        # Fallback for process exit without a window close (e.g. script ends
        # before the user closes the viewer).
        atexit.register(_weak_cleanup)

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

    @property
    def core(self) -> CMMCorePlus:
        """The CMMCorePlus instance currently used by this window."""
        return self._mmc

    def set_core(self, core: CMMCorePlus, owns: bool = False) -> None:
        """Install *core*, tearing down the previous one if present.

        Parameters
        ----------
        core : CMMCorePlus
            The core to install.
        owns : bool, default False
            Whether the plugin takes ownership of *core*. When True, the
            plugin is responsible for its lifecycle: on viewer close (and
            on the next ``set_core`` swap) it will cancel any running MDA
            and unload all devices. When False, the plugin will not cancel
            MDAs or unload devices on *core* — use this when the caller
            retains its own reference and manages the core's lifecycle
            itself.
        """
        old_link = getattr(self, "_core_link", None)
        old_owns = getattr(self, "_owns_core", False)

        # Guard: refuse if MDA is running
        if old_link is not None and old_link._mda_handler._mda_running:
            raise RuntimeError("Cannot swap core while MDA is running.")

        # Tear down old core (if any)
        if old_link is not None:
            self._unwrap_load_system_configuration(self._mmc)
            old_link.cleanup(owns=old_owns)
            old_link.setParent(None)
            old_link.deleteLater()

        # Install new core
        self._mmc = core
        self._owns_core = owns
        self._core_link = CoreViewerLink(self.viewer, self._mmc, self)
        self._wrap_load_system_configuration(self._mmc)

        # Rebuild UI (only needed when swapping, not on first init)
        if old_link is not None:
            self._rebuild_toolbars(self._mmc)
            self._close_all_dock_widgets()
            if console := getattr(self.viewer.window._qt_viewer, "console", None):
                console.push({"mmcore": self._mmc})

    _ORIGINAL_LOAD_ATTR = "_nmm_original_loadSystemConfiguration"

    def _wrap_load_system_configuration(self, core: CMMCorePlus) -> None:
        """Monkey-patch loadSystemConfiguration to auto-detect #py cfg files."""
        import weakref

        from pymmcore_plus.experimental.unicore import UniMMCore

        # Restore original if previously wrapped (prevents double-wrap stacking)
        original = getattr(core, self._ORIGINAL_LOAD_ATTR, None)
        if original is None:
            original = core.loadSystemConfiguration
            setattr(core, self._ORIGINAL_LOAD_ATTR, original)
        else:
            core.loadSystemConfiguration = original  # type: ignore[method-assign]

        weak_self = weakref.ref(self)

        def _auto_detect_load(path: str | Path) -> None:
            win = weak_self()
            if win is None:
                original(path)
                return

            needs_unicore = _cfg_has_py_devices(path)
            is_unicore = isinstance(win._mmc, UniMMCore)

            if needs_unicore and not is_unicore:
                win.set_core(UniMMCore(), owns=True)
                win._mmc.loadSystemConfiguration(path)
                return
            if not needs_unicore and is_unicore:
                win.set_core(CMMCorePlus(), owns=True)
                win._mmc.loadSystemConfiguration(path)
                return

            original(path)

        core.loadSystemConfiguration = _auto_detect_load  # type: ignore[assignment,method-assign]

    def _unwrap_load_system_configuration(self, core: CMMCorePlus) -> None:
        """Restore original loadSystemConfiguration if it was wrapped."""
        if original := getattr(core, self._ORIGINAL_LOAD_ATTR, None):
            core.loadSystemConfiguration = original  # type: ignore[method-assign]
            delattr(core, self._ORIGINAL_LOAD_ATTR)

    def _cleanup(self) -> None:
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True
        self._unwrap_load_system_configuration(self._mmc)
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Break the self._connections → tuple → bound method → self cycle.
        self._connections.clear()
        # `_core_link.cleanup()` issues `stopSequenceAcquisition()` to the
        # camera adapter. If the device is unresponsive this can raise (or
        # block); don't let that abort the rest of teardown, including
        # atexit-unregister.
        with contextlib.suppress(Exception):
            self._core_link.cleanup(owns=self._owns_core)
        atexit.unregister(self._weak_cleanup)

    def _update_max_min(self, *_: Any) -> None:
        visible = (x for x in self.viewer.layers.selection if x.visible)
        self.minmax.update_from_layers(
            lr for lr in visible if isinstance(lr, napari.layers.Image)
        )
