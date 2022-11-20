from typing import Optional

from pymmcore_widgets import GroupPresetTableWidget
from qtpy.QtWidgets import QDialog, QSizePolicy, QVBoxLayout, QWidget


class GroupPreset(QDialog):
    """Group and Preset Widget."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Groups & Presets")

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self._gp = GroupPresetTableWidget()
        self._gp._mmc.mda.events.sequenceStarted.connect(self._on_started)
        self._gp._mmc.mda.events.sequenceFinished.connect(self._on_finished)
        self.layout().addWidget(self._gp)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def _on_started(self) -> None:
        self.setEnabled(False)

    def _on_finished(self) -> None:
        self.setEnabled(True)
