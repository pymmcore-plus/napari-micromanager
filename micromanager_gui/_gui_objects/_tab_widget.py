from pathlib import Path
from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (
    CameraRoiWidget,
    ChannelWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    ObjectivesWidget,
    SnapButton,
)
from qtpy import QtCore
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QCheckBox, QWidget
from superqt.fonticon import icon
from superqt.utils import create_worker

from ._illumination_widget import IlluminationWidget
from ._xyz_stages import MMStagesWidget

COLOR_TYPES = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


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

        # add objectives
        obj = self.add_mm_objectives_widget()
        self.snap_live_tab_layout.addWidget(obj, 0, 0, 1, 3)

        # channel in snap_live_tab
        self.snap_channel_groupBox = QtW.QGroupBox()
        self.snap_channel_groupBox.setSizePolicy(wdg_sizepolicy)
        self.snap_channel_groupBox.setTitle("Channel")
        self.snap_channel_groupBox_layout = QtW.QHBoxLayout()
        self.snap_channel_comboBox = ChannelWidget()
        self.snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
        self.snap_channel_groupBox.setLayout(self.snap_channel_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.snap_channel_groupBox, 1, 0)

        # exposure in snap_live_tab
        self.exposure_widget = DefaultCameraExposureWidget()
        self.exp_groupBox = QtW.QGroupBox()
        self.exp_groupBox.setSizePolicy(wdg_sizepolicy)
        self.exp_groupBox.setTitle("Exposure Time")
        self.exp_groupBox_layout = QtW.QHBoxLayout()
        self.exp_groupBox_layout.addWidget(self.exposure_widget)
        self.exp_groupBox.setLayout(self.exp_groupBox_layout)
        self.snap_live_tab_layout.addWidget(self.exp_groupBox, 1, 1)

        # stage
        self.stage_groupBox = QtW.QGroupBox()
        self.stage_groupBox.setMinimumWidth(100)
        self.stage_groupBox.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum)
        )
        self.stage_groupBox.setTitle("Stages")
        self.stage_groupBox_layout = QtW.QHBoxLayout()
        self.stage_groupBox.setLayout(self.stage_groupBox_layout)
        self.stage_btn = QtW.QPushButton()
        self.stage_btn.setIcon(icon(MDI6.cursor_move, color=(0, 255, 0)))
        self.stage_btn.setIconSize(QSize(25, 25))
        self.stage_btn.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        self.stage_btn.clicked.connect(self._show_stage_wdg)
        self.stage_groupBox_layout.addWidget(self.stage_btn)
        self.snap_live_tab_layout.addWidget(self.stage_groupBox, 1, 2)

        # snap/live
        wdg = QtW.QGroupBox()
        wdg_layout = QtW.QVBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)

        # snap/live in snap_live_tab

        self._talley_cbox = QCheckBox()
        self._talley_cbox.setFixedWidth(20)
        self._talley_cbox.setStyleSheet(
            "QCheckBox::indicator" "{" "background-color : rgb(38, 41, 48);" "}"
        )

        self.btn_wdg = QtW.QWidget()
        self.btn_wdg.setMaximumHeight(65)

        self.btn_wdg_layout = QtW.QHBoxLayout()
        self.snap_Button = _SnapButton(checkbox=self._talley_cbox)
        self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.snap_Button)
        self.live_Button = LiveButton()
        self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
        self.btn_wdg_layout.addWidget(self.live_Button)
        self.btn_wdg.setLayout(self.btn_wdg_layout)
        wdg_layout.addWidget(self.btn_wdg)

        # max min in snap_live_tab
        self.max_min_wdg = QtW.QWidget()
        self.max_min_wdg_layout = QtW.QHBoxLayout()
        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        self.max_min_val_label = QtW.QLabel()
        self.max_min_wdg_layout.addWidget(self._talley_cbox)
        self.max_min_wdg_layout.addWidget(self.max_min_val_label_name)
        self.max_min_wdg_layout.addWidget(self.max_min_val_label)

        self.max_min_wdg.setLayout(self.max_min_wdg_layout)
        wdg_layout.addWidget(self.max_min_wdg)
        self.snap_live_tab_layout.addWidget(wdg, 2, 0, 1, 3)

        # set snap_live_tab layout
        self.snap_live_tab.setLayout(self.snap_live_tab_layout)

        # add illumination
        ill_group = QtW.QGroupBox()
        ill_group.setTitle("Illumination")
        ill_group_layout = QtW.QVBoxLayout()
        ill_group_layout.setSpacing(0)
        ill_group_layout.setContentsMargins(10, 10, 10, 10)
        ill_group.setLayout(ill_group_layout)
        self.ill = IlluminationWidget()
        ill_group_layout.addWidget(self.ill)
        self.snap_live_tab_layout.addWidget(ill_group, 3, 0, 1, 3)

        # add camera
        cam_group = QtW.QGroupBox()
        cam_group.setTitle("Camera ROI")
        cam_group_layout = QtW.QVBoxLayout()
        cam_group_layout.setSpacing(0)
        cam_group_layout.setContentsMargins(3, 8, 3, 3)
        cam_group.setLayout(cam_group_layout)
        self.cam_wdg = CameraRoiWidget()
        cam_group_layout.addWidget(self.cam_wdg)
        self.snap_live_tab_layout.addWidget(cam_group, 4, 0, 1, 3)

        # spacer
        spacer = QtW.QSpacerItem(
            20, 40, QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Expanding
        )
        self.snap_live_tab_layout.addItem(spacer, 5, 0)

        # add tabWidget
        self.tabWidget.setLayout(self.tabWidget_layout)
        self.tabWidget.addTab(self.snap_live_tab, "General")
        self.main_layout.addWidget(self.tabWidget)

        # Set main layout
        self.setLayout(self.main_layout)

    def add_mm_objectives_widget(self):
        self.obj_wdg = ObjectivesWidget()
        obj_wdg = QtW.QGroupBox()
        obj_wdg_layout = QtW.QHBoxLayout()
        obj_wdg_layout.setContentsMargins(5, 5, 5, 5)
        obj_wdg_layout.setSpacing(7)
        obj_wdg.setLayout(obj_wdg_layout)
        obj_wdg_layout.addWidget(self.obj_wdg)

        return obj_wdg

    def _show_stage_wdg(self):
        if not hasattr(self, "stage_wdg"):
            self.stage_wdg = MMStagesWidget(parent=self)
        self.stage_wdg.show()
        self.stage_wdg.raise_()


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMTabWidget()
    win.show()
    sys.exit(app.exec_())


class _SnapButton(SnapButton):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
        checkbox: QCheckBox
    ) -> None:

        super().__init__(parent=parent, mmcore=mmcore)

        self._mmc = mmcore or CMMCorePlus.instance()
        self.checkbox = checkbox

        self.clicked.connect(self._snap)

    def _snap(self) -> None:
        if self._mmc.isSequenceRunning():
            self._mmc.stopSequenceAcquisition()
        if self._mmc.getAutoShutter():
            self._mmc.events.propertyChanged.emit(
                self._mmc.getShutterDevice(), "State", True
            )
        if self.checkbox.isChecked():
            import imageio as io

            img = Path(__file__).parent.parent.parent / "talley.png"
            self._mmc.events.imageSnapped.emit(io.imread(img))
        else:
            create_worker(self._mmc.snap, _start_thread=True)
