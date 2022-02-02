from pathlib import Path

from qtpy import QtCore
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

ICONS = Path(__file__).parent.parent / "icons"


class MMTabWidget(QtW.QWidget):
    """
    Contains the following objects:

    tabWidget: QtW.QTabWidget
    snap_live_tab: QtW.QWidget
    snap_channel_groupBox: QtW.QGroupBox
    snap_channel_comboBox: QtW.QComboBox
    exp_groupBox: QtW.QGroupBox
    exp_spinBox: QtW.QDoubleSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton
    max_min_val_label: QtW.QLabel
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

        for attr, icon in [
            ("snap_Button", "cam.svg"),
            ("live_Button", "vcam.svg"),
        ]:
            btn = getattr(self, attr)
            btn.setIcon(QIcon(str(ICONS / icon)))
            btn.setIconSize(QSize(30, 30))

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()

        self.tabWidget = QtW.QTabWidget()

        self.snap_live_tab = QtW.QWidget()
        self.snap_live_tab_layout = QtW.QGridLayout()

        # channel
        self.snap_channel_groupBox = QtW.QGroupBox()
        self.snap_channel_groupBox.setMaximumHeight(70)
        self.snap_channel_groupBox.setTitle("Channel")

        self.snap_channel_groupBox_layout = QtW.QGridLayout()
        self.snap_channel_comboBox = QtW.QComboBox()
        self.snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox, 0, 0)
        self.snap_channel_groupBox.setLayout(self.snap_channel_groupBox_layout)

        self.snap_live_tab_layout.addWidget(self.snap_channel_groupBox, 0, 0)
        # exposure
        self.exp_groupBox = QtW.QGroupBox()
        self.exp_groupBox.setMaximumHeight(70)
        self.exp_groupBox.setTitle("Exposure Time")

        self.exp_groupBox_layout = QtW.QGridLayout()
        self.exp_label = QtW.QLabel()
        self.exp_label.setText(" ms")
        self.exp_label.setMaximumWidth(30)
        self.exp_spinBox = QtW.QDoubleSpinBox()
        self.exp_spinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.exp_spinBox.setMinimum(1.0)
        self.exp_spinBox.setMaximum(100000.0)
        self.exp_groupBox_layout.addWidget(self.exp_spinBox, 0, 0)
        self.exp_groupBox_layout.addWidget(self.exp_label, 0, 1)
        self.exp_groupBox.setLayout(self.exp_groupBox_layout)

        self.snap_live_tab_layout.addWidget(self.exp_groupBox, 0, 1)
        # snap/live
        self.btn_wdg = QtW.QWidget()
        self.btn_wdg.setMaximumHeight(65)
        self.btn_wdg_layout = QtW.QGridLayout()

        self.snap_Button = QtW.QPushButton(text="Snap")
        self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.snap_Button, 0, 0)

        self.live_Button = QtW.QPushButton(text="Live")
        self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.live_Button, 0, 1)

        self.btn_wdg.setLayout(self.btn_wdg_layout)
        self.snap_live_tab_layout.addWidget(self.btn_wdg, 1, 0, 1, 2)
        # max min
        self.max_min_wdg = QtW.QWidget()
        self.max_min_wdg_layout = QtW.QGridLayout()

        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        self.max_min_val_label = QtW.QLabel()

        self.max_min_wdg_layout.addWidget(self.max_min_val_label_name, 0, 0)
        self.max_min_wdg_layout.addWidget(self.max_min_val_label, 0, 1)

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
        self.tabWidget.addTab(self.snap_live_tab, "Snap/Live")

        self.main_layout.addWidget(self.tabWidget)
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMTabWidget()
    win.show()
    sys.exit(app.exec_())
