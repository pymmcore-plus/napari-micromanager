from typing import Optional

from pymmcore_widgets import CameraRoiWidget
from qtpy.QtWidgets import QDialog, QSizePolicy, QVBoxLayout, QWidget


class CamROI(QDialog):
    """Camera ROI Widget."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Camera ROI")

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self._cam = CameraRoiWidget()
        self._cam._mmc.mda.events.sequenceStarted.connect(self._on_started)
        self._cam._mmc.mda.events.sequenceFinished.connect(self._on_finished)
        self.layout().addWidget(self._cam)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def _on_started(self) -> None:
        self.setEnabled(False)

    def _on_finished(self) -> None:
        self.setEnabled(True)
