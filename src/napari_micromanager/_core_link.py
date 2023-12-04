from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Callable

import napari
import napari.layers
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QObject, Qt, QTimerEvent
from superqt.utils import ensure_main_thread

from ._mda_handler import _NapariMDAHandler

if TYPE_CHECKING:
    import napari.viewer
    import numpy as np
    from pymmcore_plus.core.events._protocol import PSignalInstance


class CoreViewerLink(QObject):
    """QObject linking events in a napari viewer to events in a CMMCorePlus instance."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        core: CMMCorePlus | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._mmc = core or CMMCorePlus.instance()
        self.viewer = viewer
        self._mda_handler = _NapariMDAHandler(self._mmc, viewer)
        self._live_timer_id: int | None = None

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.events.imageSnapped, self._update_viewer),
            (self._mmc.events.imageSnapped, self._stop_live),
            (self._mmc.events.continuousSequenceAcquisitionStarted, self._start_live),
            (self._mmc.events.sequenceAcquisitionStopped, self._stop_live),
            (self._mmc.events.exposureChanged, self._restart_live),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

    def cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._mda_handler._cleanup()

    def timerEvent(self, a0: QTimerEvent | None) -> None:
        self._update_viewer()

    def _start_live(self) -> None:
        interval = int(self._mmc.getExposure())
        self._live_timer_id = self.startTimer(interval, Qt.TimerType.PreciseTimer)

    def _stop_live(self) -> None:
        if self._live_timer_id is not None:
            self.killTimer(self._live_timer_id)
            self._live_timer_id = None

    def _restart_live(self, camera: str, exposure: float) -> None:
        if self._live_timer_id:
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition()

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

        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            preview_layer.scale = (pix_size, pix_size)
        else:
            # return to default
            preview_layer.scale = [1.0, 1.0]

        if self._live_timer_id is None:
            self.viewer.reset_view()
