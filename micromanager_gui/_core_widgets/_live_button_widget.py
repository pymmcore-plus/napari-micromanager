from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6

# from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QPushButton
from superqt.fonticon import icon

from .._core import get_core_singleton

COLOR_TYPE = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class LiveButton(QPushButton):
    """Create a two-state (on-off) live mode QPushButton.

    When pressed, a 'ContinuousSequenceAcquisition' is started or stopped
    and a pymmcore-plus signal 'startContinuousSequenceAcquisition' or
    'stopSequenceAcquisition' is emitted.

    Parameters
    ----------
    button_text_on_off : Optional[tuple[str, str]]
        Text of the QPushButton in the on and off state.
    icon_size : Optional[int]
        Size of the QPushButton icon.
    icon_color_on_off : Optional[tuple[COLOR_TYPE, COLOR_TYPE]]
       Color of the QPushButton icon in the on and off state.
    """

    def __init__(
        self,
        button_text_on_off: Tuple[str, str] = ("", ""),
        icon_size: int = 30,
        icon_color_on_off: Tuple[COLOR_TYPE, COLOR_TYPE] = ("", ""),
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ) -> None:

        super().__init__()

        self._mmc = mmcore or get_core_singleton()
        self._camera = self._mmc.getCameraDevice()
        self.button_text_on = button_text_on_off[0]
        self.button_text_off = button_text_on_off[1]
        self.icon_size = icon_size
        self.icon_color_on = icon_color_on_off[0]
        self.icon_color_off = icon_color_on_off[1]

        self.streaming_timer = None

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._on_system_cfg_loaded()
        self._mmc.events.startContinuousSequenceAcquisition.connect(
            self._on_sequence_started
        )
        self._mmc.events.stopSequenceAcquisition.connect(self._on_sequence_stopped)
        self.destroyed.connect(self.disconnect)

        self._create_button()

        self.setEnabled(False)
        if len(self._mmc.getLoadedDevices()) > 1:
            self.setEnabled(True)

    def _create_button(self):
        if self.button_text_on:
            self.setText(self.button_text_on)
        self.set_icon_state(False)
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        self.clicked.connect(self.toggle_live_mode)

    def _on_system_cfg_loaded(self):
        self._camera = self._mmc.getCameraDevice()
        self.setEnabled(bool(self._camera))

    def toggle_live_mode(self):
        """Start/stop SequenceAcquisition."""
        if self._mmc.isSequenceRunning(self._camera):
            self._mmc.stopSequenceAcquisition(self._camera)  # pymmcore-plus method
            self.set_icon_state(False)
        else:
            self._mmc.startContinuousSequenceAcquisition()  # pymmcore-plus method
            self.set_icon_state(True)

    def set_icon_state(self, state: bool):
        """Set the icon in the on or off state."""
        if state:  # set in the off mode
            self.setIcon(icon(MDI6.video_off_outline, color=self.icon_color_off))
            if self.button_text_off:
                self.setText(self.button_text_off)
        else:  # set in the on mode
            self.setIcon(icon(MDI6.video_outline, color=self.icon_color_on))
            if self.button_text_on:
                self.setText(self.button_text_on)

    def _on_sequence_started(self):
        self.set_icon_state(True)

    def _on_sequence_stopped(self, camera: str):
        self.set_icon_state(False)

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )
        self._mmc.events.startContinuousSequenceAcquisition.disconnect(
            self._on_sequence_started
        )
        self._mmc.events.stopSequenceAcquisition.disconnect(self._on_sequence_stopped)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = LiveButton()
    win.show()
    sys.exit(app.exec_())
