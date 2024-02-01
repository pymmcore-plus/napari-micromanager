from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Callable

import napari
import napari.layers
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QObject, Qt, QTimer
from superqt.utils import ensure_main_thread

from ._mda_handler import _NapariMDAHandler

if TYPE_CHECKING:
    import napari.viewer
    import numpy as np
    from pymmcore_plus.core.events._protocol import PSignalInstance


_DEFAULT_WAIT = 100  # ms


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

        self.streaming_timer = QTimer(parent=self)
        self.streaming_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.streaming_timer.setInterval(int(self._mmc.getExposure()) or _DEFAULT_WAIT)
        self.streaming_timer.timeout.connect(self._on_streaming_timeout)

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.events.imageSnapped, self._on_image_snapped),
            (self._mmc.events.imageSnapped, self._stop_live),
            (self._mmc.events.continuousSequenceAcquisitionStarted, self._start_live),
            (self._mmc.events.sequenceAcquisitionStopped, self._stop_live),
            (self._mmc.events.exposureChanged, self._on_exposure_changed),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

    def _on_streaming_timeout(self) -> None:
        with contextlib.suppress(RuntimeError, IndexError):
            self._update_viewer(self._mmc.getLastImage())

    def _start_live(self) -> None:
        self.streaming_timer.start()

    def _stop_live(self) -> None:
        self.streaming_timer.stop()

    def _on_exposure_changed(self, device: str, value: str) -> None:
        self.streaming_timer.setInterval(int(value))

    def _on_image_snapped(self) -> None:
        self._update_viewer(self._mmc.getImage())

    def cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._mda_handler._cleanup()

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

        # if self._live_timer_id is None:
        if not self._mmc.isSequenceRunning():
            self.viewer.reset_view()
