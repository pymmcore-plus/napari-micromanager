from typing import Optional, Tuple, Union

from pymmcore_plus import CMMCorePlus
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from micromanager_gui._core import get_core_singleton  # to test, to be replaced

# from micromanager_gui._util import set_wdg_color  # to test, to be replaced

COLOR_TYPE = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class MMShuttersWidget(QtW.QWidget):
    """A Widget for shutters and Micro-Manager autoshutter.

    Parameters
    ----------
    shutter_device: str:
        The shutter device Label.
    button_text_open_closed: Optional[tuple[str, str]]
       Text of the QPushButton when the shutter is open or closed
    icon_size : Optional[str]
        Size of the QPushButton icon.
    icon_color_open_closed : Optional[COLOR_TYPE]
        Color of the QPushButton icon when the shutter is open or closed.
    text_color_combo:
        Text color of the shutter QComboBox.
    parent : Optional[QWidget]
        Optional parent widget.

    COLOR_TYPE = Union[QColor, int, str, Qt.GlobalColor, Tuple[int, int, int, int],
    Tuple[int, int, int]]
    """

    def __init__(
        self,
        shutter_device: str,
        button_text_open_closed: Optional[tuple[str, str]] = (None, None),
        icon_size: Optional[int] = 25,
        icon_color_open_closed: Optional[tuple[COLOR_TYPE, COLOR_TYPE]] = (
            "black",
            "black",
        ),
        text_color_combo: Optional[COLOR_TYPE] = "black",
        parent: Optional[QtW.QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__()
        self._mmc = mmcore or get_core_singleton()

        self._mmc.loadSystemConfiguration(
            "/Users/FG/Desktop/test_config_multishutter.cfg"
        )  # to test, to be removed

        self.shutter = shutter_device

        self.button_text_open = button_text_open_closed[0]
        self.button_text_closed = button_text_open_closed[1]
        self.icon_size = icon_size
        self.icon_color_open = icon_color_open_closed[0]
        self.icon_color_closed = icon_color_open_closed[1]
        self.text_color_combo = text_color_combo
