from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6

# from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QPushButton
from superqt.fonticon import icon

from micromanager_gui._core import get_core_singleton

COLOR_TYPE = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class LiveButton(QPushButton):
    """
    Create a two-state (on-off) live mode QPushButton. When toggled on,
    an empty signal is emitted ('_emitFrameSignal') through a QTimer.
    """

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
        button_text_on_off: Optional[tuple[str, str]] = (None, None),
        icon_size: Optional[int] = 30,
        icon_color_on_off: Optional[tuple[COLOR_TYPE, COLOR_TYPE]] = ("black", "black"),
    ) -> None:

        super().__init__()

        self._mmc = mmcore or get_core_singleton()
        self.button_text_on = button_text_on_off[0]
        self.button_text_off = button_text_on_off[1]
        self.icon_size = icon_size
        self.icon_color_on = icon_color_on_off[0]
        self.icon_color_off = icon_color_on_off[1]

        self.streaming_timer = None

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._on_system_cfg_loaded()
        self._mmc.events.continuousSequenceAcquisition.connect(self.set_icon_state)
        self.destroyed.connect(self.disconnect)

        self._create_button()

    def _create_button(self):
        if self.button_text_on:
            self.setText(self.button_text_on)
        self.set_icon_state(False)
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        self.clicked.connect(self.toggle_live_mode)

    def _on_system_cfg_loaded(self):
        self.setEnabled(bool(self._mmc.getCameraDevice()))

    def toggle_live_mode(self):
        """start/stop SequenceAcquisition"""
        if self._mmc.isSequenceRunning():
            self._mmc.stopSeqAcquisition()  # pymmcore-plus method
            self.set_icon_state(False)
        else:
            self._mmc.startContinuousSeqAcquisition()  # pymmcore-plus method
            self.set_icon_state(True)

    def set_icon_state(self, state: bool):
        """set the icon in the on or off state"""
        if state:  # set in the off mode
            self.setIcon(icon(MDI6.video_off_outline, color=self.icon_color_off))
            if self.button_text_off:
                self.setText(self.button_text_off)
        else:  # set in the on mode
            self.setIcon(icon(MDI6.video_outline, color=self.icon_color_on))
            if self.button_text_on:
                self.setText(self.button_text_on)

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )
        self._mmc.events.continuousSequenceAcquisition.disconnect(self.set_icon_state)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = LiveButton()
    win.show()
    sys.exit(app.exec_())
