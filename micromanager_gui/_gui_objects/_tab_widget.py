from pathlib import Path

from pymmcore_widgets import (
    ChannelWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    SnapButton,
)
from qtpy import QtCore
from qtpy import QtWidgets as QtW

ICONS = Path(__file__).parent.parent / "icons"


class MMTabWidget(QtW.QWidget):
    """Tabs shown in the main window."""

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        # main_layout
        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # tabWidget
        self.tabWidget = QtW.QTabWidget()
        self.tabWidget.setMovable(True)
        self.tabWidget_layout = QtW.QVBoxLayout()

        sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        self.tabWidget.setSizePolicy(sizepolicy)

        # snap_live_tab and layout
        self.snap_live_tab = QtW.QWidget()
        self.snap_live_tab_layout = QtW.QGridLayout()

        wdg_sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum
        )

        # channel in snap_live_tab
        self.snap_channel_groupBox = QtW.QGroupBox()
        self.snap_channel_groupBox.setSizePolicy(wdg_sizepolicy)
        self.snap_channel_groupBox.setTitle("Channel")
        self.snap_channel_groupBox_layout = QtW.QHBoxLayout()
        self.snap_channel_comboBox = ChannelWidget()
        self.snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
        self.snap_channel_groupBox.setLayout(self.snap_channel_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.snap_channel_groupBox, 0, 0)

        # exposure in snap_live_tab
        self.exposure_widget = DefaultCameraExposureWidget()
        self.exp_groupBox = QtW.QGroupBox()
        self.exp_groupBox.setSizePolicy(wdg_sizepolicy)
        self.exp_groupBox.setTitle("Exposure Time")
        self.exp_groupBox_layout = QtW.QHBoxLayout()
        self.exp_groupBox_layout.addWidget(self.exposure_widget)
        self.exp_groupBox.setLayout(self.exp_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.exp_groupBox, 0, 1)

        # snap/live in snap_live_tab
        self.btn_wdg = QtW.QWidget()
        self.btn_wdg.setMaximumHeight(65)
        self.btn_wdg_layout = QtW.QHBoxLayout()
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

        # max min in snap_live_tab
        self.max_min_wdg = QtW.QWidget()
        self.max_min_wdg_layout = QtW.QHBoxLayout()
        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        self.max_min_val_label = QtW.QLabel()
        self.max_min_wdg_layout.addWidget(self.max_min_val_label_name)
        self.max_min_wdg_layout.addWidget(self.max_min_val_label)
        self.max_min_wdg.setLayout(self.max_min_wdg_layout)
        self.snap_live_tab_layout.addWidget(self.max_min_wdg, 2, 0, 1, 2)

        # spacer
        spacer = QtW.QSpacerItem(
            20, 40, QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Expanding
        )
        self.snap_live_tab_layout.addItem(spacer, 3, 0)

        # set snap_live_tab layout
        self.snap_live_tab.setLayout(self.snap_live_tab_layout)

        # add tabWidget
        self.tabWidget.setLayout(self.tabWidget_layout)
        self.tabWidget.addTab(self.snap_live_tab, "Snap/Live")
        self.main_layout.addWidget(self.tabWidget)

        # Set main layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMTabWidget()
    win.show()
    sys.exit(app.exec_())
