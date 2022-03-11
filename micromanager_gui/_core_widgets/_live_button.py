from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6

# from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt, QTimer, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QPushButton
from superqt.fonticon import icon
from superqt.utils import create_worker

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
    """Create a live QPushButton"""

    emitFrame = Signal()

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
        self.destroyed.connect(self.disconnect)

        self._create_button()

    def _emit(self):
        create_worker(self.emitFrame.emit, _start_thread=True)

    def _create_button(self):
        if self.button_text_on:
            self.setText(self.button_text_on)
        self.set_icon_state(True)
        self.clicked.connect(self.toggle_live)

    def _on_system_cfg_loaded(self):
        self.setEnabled(bool(self._mmc.getCameraDevice()))

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )

    def set_icon_state(self, state: bool):
        """set the icon in the on or off state"""
        if state:
            self.setIcon(icon(MDI6.video_outline, color=self.icon_color_on))
            if self.button_text_on:
                self.setText(self.button_text_on)

        else:
            self.setIcon(icon(MDI6.video_off_outline, color=self.icon_color_off))
            if self.button_text_off:
                self.setText(self.button_text_off)
        self.setIconSize(QSize(self.icon_size, self.icon_size))

    def start_live(self):
        self._mmc.startContinuousSequenceAcquisition(self._mmc.getExposure())
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self._emit)
        self.streaming_timer.start(self._mmc.getExposure())
        self.set_icon_state(True)

    def stop_live(self):
        self._mmc.stopSequenceAcquisition()
        if self.streaming_timer is not None:
            self.streaming_timer.stop()
            self.streaming_timer = None
        self.set_icon_state(False)

    def toggle_live(self, event=None):
        if self.streaming_timer is None:

            if not self._mmc.getChannelGroup():
                return

            self.start_live()
            self.set_icon_state(False)
        else:
            self.stop_live()
            self.set_icon_state(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = LiveButton()
    win.show()
    sys.exit(app.exec_())
