from pathlib import Path

from pymmcore_widgets import (
    ChannelWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    SnapButton,
)
from qtpy import QtCore
from qtpy.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ICONS = Path(__file__).parent.parent / "icons"


class SnapLiveWidget(QWidget):
    """Tabs shown in the main window."""

    def __init__(self) -> None:
        super().__init__()
        self._create_gui()

    def _create_gui(self) -> None:
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.snap_live_tab = QGroupBox()
        self.snap_live_tab.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.snap_live_tab_layout = QGridLayout()

        wdg_sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        # channel in snap_live_tab
        self.snap_channel_groupBox = QGroupBox()
        self.snap_channel_groupBox.setSizePolicy(wdg_sizepolicy)
        self.snap_channel_groupBox.setTitle("Channel")
        self.snap_channel_groupBox_layout = QHBoxLayout()
        self.snap_channel_comboBox = ChannelWidget()
        self.snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
        self.snap_channel_groupBox.setLayout(self.snap_channel_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.snap_channel_groupBox, 0, 0)

        # exposure in snap_live_tab
        self.exposure_widget = DefaultCameraExposureWidget()
        self.exp_groupBox = QGroupBox()
        self.exp_groupBox.setSizePolicy(wdg_sizepolicy)
        self.exp_groupBox.setTitle("Exposure Time")
        self.exp_groupBox_layout = QHBoxLayout()
        self.exp_groupBox_layout.addWidget(self.exposure_widget)
        self.exp_groupBox.setLayout(self.exp_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.exp_groupBox, 0, 1)

        # snap/live in snap_live_tab
        self.btn_wdg = QWidget()
        self.btn_wdg.setMaximumHeight(65)
        self.btn_wdg_layout = QHBoxLayout()
        self.snap_Button = SnapButton()
        self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.snap_Button)
        self.live_Button = LiveButton()
        self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.live_Button)
        self.btn_wdg.setLayout(self.btn_wdg_layout)
        self.snap_live_tab_layout.addWidget(self.btn_wdg, 1, 0, 1, 2)
        self.snap_live_tab.setLayout(self.snap_live_tab_layout)

        self.main_layout.addWidget(self.snap_live_tab)
