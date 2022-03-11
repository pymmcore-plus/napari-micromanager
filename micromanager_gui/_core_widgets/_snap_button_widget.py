from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QPushButton
from superqt.fonticon import icon

from micromanager_gui._core import get_core_singleton


class SnapButton(QPushButton):
    """
    Create a snap QPushButton linked to the pymmcore-plus 'snap()' method.
    Once the button is clicked, an image is snapped and the pymmcore-plus
    'imageSnapped' signal is emitted.
    """

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
        button_text: Optional[str] = None,
        icon_size: Optional[int] = 30,
        icon_color: Optional[
            Union[
                QColor,
                int,
                str,
                Qt.GlobalColor,
                Tuple[int, int, int, int],
                Tuple[int, int, int],
            ]
        ] = "black",
    ) -> None:

        super().__init__()

        self._mmc = mmcore or get_core_singleton()
        self.button_text = button_text
        self.icon_size = icon_size
        self.icon_color = icon_color

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._on_system_cfg_loaded()
        self.destroyed.connect(self.disconnect)

        self._create_button()

    def _create_button(self):
        if self.button_text:
            self.setText(self.button_text)
        self.setIcon(icon(MDI6.camera_outline, color=self.icon_color))
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        self.clicked.connect(self._snap)

    def _snap(self):
        if self._mmc.isSequenceRunning():
            self._mmc.stopSequenceAcquisition()

        try:
            self._mmc.snap()
        except RuntimeError:
            raise

    def _on_system_cfg_loaded(self):
        self.setEnabled(bool(self._mmc.getCameraDevice()))

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = SnapButton()
    win.show()
    sys.exit(app.exec_())
