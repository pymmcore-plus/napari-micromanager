from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QPushButton, QSizePolicy
from superqt.fonticon import icon
from superqt.utils import create_worker

from .._core import get_core_singleton

COLOR_TYPES = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class SnapButton(QPushButton):
    """Create a snap QPushButton linked to the pymmcore-plus 'snap()' method.

    Once the button is clicked, an image is acquired and the pymmcore-plus
    'imageSnapped(image: nparray)' signal is emitted.

    Parameters
    ----------
    camera:
        Camera device. If 'None' -> getCameraDevice()
    button_text : Optional[str]
        Text of the QPushButton.
    icon_size : Optional[int]
        Size of the QPushButton icon.
    icon_color : Optional[COLOR_TYPE]
       Color of the QPushButton icon in the on and off state.
    """

    def __init__(
        self,
        camera: Optional[str] = None,
        button_text: Optional[str] = None,
        icon_size: Optional[int] = 30,
        icon_color: Optional[COLOR_TYPES] = "",
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ) -> None:

        super().__init__()

        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))

        self._mmc = mmcore or get_core_singleton()
        self._camera = camera or self._mmc.getCameraDevice()
        self.button_text = button_text
        self.icon_size = icon_size
        self.icon_color = icon_color

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._on_system_cfg_loaded()
        self.destroyed.connect(self.disconnect)

        self._create_button()

        self.setEnabled(False)
        if len(self._mmc.getLoadedDevices()) > 1:
            self.setEnabled(True)

    def _create_button(self):
        if self.button_text:
            self.setText(self.button_text)
        self.setIcon(icon(MDI6.camera_outline, color=self.icon_color))
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        self.clicked.connect(self._snap)

    def _snap(self):
        if self._mmc.isSequenceRunning(self._camera):
            self._mmc.stopSequenceAcquisition(self._camera)
        if self._mmc.getAutoShutter():
            self._mmc.events.propertyChanged.emit(
                self._mmc.getShutterDevice(), "State", True
            )
        create_worker(self._mmc.snap, _start_thread=True)

    def _on_system_cfg_loaded(self):
        if not self._camera:
            self._camera = self._mmc.getCameraDevice()
        self.setEnabled(bool(self._camera))

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )
