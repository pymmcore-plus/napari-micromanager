from __future__ import annotations

import atexit
import contextlib
from typing import TYPE_CHECKING, Any, Callable

import napari
import numpy as np
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor
from superqt.utils import create_worker, ensure_main_thread

from ._gui_objects._toolbar import MicroManagerToolbar
from ._mda_handler import _NapariMDAHandler

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    from pymmcore_plus.core.events._protocol import PSignalInstance


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`mmcore install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        super().__init__(viewer)

        # get global CMMCorePlus instance
        self._mmc = CMMCorePlus.instance()
        self.viewer = viewer

        self._mda_handler = _NapariMDAHandler(self._mmc, viewer)
        self.streaming_timer: QTimer | None = None

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.events.exposureChanged, self._update_live_exp),
            (self._mmc.events.imageSnapped, self._update_viewer),
            (self._mmc.events.imageSnapped, self._stop_live),
            (self._mmc.events.continuousSequenceAcquisitionStarted, self._start_live),
            (self._mmc.events.sequenceAcquisitionStopped, self._stop_live),
            (self.viewer.layers.events, self._update_max_min),
            (self.viewer.layers.selection.events, self._update_max_min),
            (self.viewer.dims.events.current_step, self._update_max_min),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

        # add minmax dockwidget
        self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._mda_handler._cleanup()
        atexit.unregister(self._cleanup)  # doesn't raise if not connected

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer(self, data: np.ndarray | None = None) -> None:
        """Update viewer with the latest image from the circular buffer."""
        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        preview_layer.metadata["mode"] = "preview"

        self._update_max_min()

        if self.streaming_timer is None:
            self.viewer.reset_view()

    def _update_max_min(self, event: Any = None) -> None:

        min_max_txt = ""
        layers: list[napari.layers.Image] = [
            lr
            for lr in self.viewer.layers.selection
            if isinstance(lr, napari.layers.Image) and lr.visible
        ]

        if not layers:
            self.minmax.max_min_val_label.setText(min_max_txt)
            return

        for layer in layers:
            col = layer.colormap.name
            if col not in QColor.colorNames():
                col = "gray"
            # min and max of current slice
            min_max_show = tuple(layer._calc_data_range(mode="slice"))
            min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self.minmax.max_min_val_label.setText(min_max_txt)

    def _snap(self) -> None:
        # update in a thread so we don't freeze UI
        create_worker(self._mmc.snap, _start_thread=True)

    def _start_live(self) -> None:
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self._update_viewer)
        self.streaming_timer.start(int(self._mmc.getExposure()))

    def _stop_live(self) -> None:
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer.deleteLater()
            self.streaming_timer = None

    def _update_live_exp(self, camera: str, exposure: float) -> None:
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)
