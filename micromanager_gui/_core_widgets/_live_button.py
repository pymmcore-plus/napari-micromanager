from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
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
    """Create a live QPushButton"""

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
        button_text: Optional[str] = None,
        icon_size: Optional[int] = 30,
        icon_color_on_off: Optional[tuple[COLOR_TYPE, COLOR_TYPE]] = ("black", "black"),
    ) -> None:

        super().__init__()

        self._mmc = mmcore or get_core_singleton()
        self.button_text = button_text
        self.icon_size = icon_size
        self.icon_color = icon_color_on_off

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._on_system_cfg_loaded()
        self.destroyed.connect(self.disconnect)

        self._create_button()

    def _create_button(self):
        if self.button_text:
            self.setText(self.button_text)
        self.set_icon_state(True)

    def _on_system_cfg_loaded(self):
        self.setEnabled(bool(self._mmc.getCameraDevice()))

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )

    def set_icon_state(self, state: bool):
        """set the icon in the on or off state"""
        if state:
            self.setIcon(icon(MDI6.video_outline, color=self.icon_color[0]))
        else:
            self.setIcon(icon(MDI6.video_off_outline, color=self.icon_color[1]))
        self.setIconSize(QSize(self.icon_size, self.icon_size))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = LiveButton()
    win.show()
    sys.exit(app.exec_())
