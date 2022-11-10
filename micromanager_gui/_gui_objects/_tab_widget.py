from typing import Tuple, Union

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
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from ._illumination_widget import IlluminationWidget

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
        self.main_tab = QtW.QWidget()
        self.main_tab_layout = QtW.QGridLayout()
        self.main_tab.setLayout(self.main_tab_layout)

        wdg_sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum
        )

        # add objectives
        obj = self.add_mm_objectives_widget()
        self.main_tab_layout.addWidget(obj, 0, 0, 1, 2)

        # channel in snap_live_tab
        snap_channel_groupBox = QtW.QGroupBox()
        snap_channel_groupBox.setSizePolicy(wdg_sizepolicy)
        snap_channel_groupBox.setTitle("Channel")
        snap_channel_groupBox_layout = QtW.QHBoxLayout()
        snap_channel_groupBox_layout.setContentsMargins(5, 5, 5, 5)
        self.snap_channel_comboBox = ChannelWidget()
        snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
        snap_channel_groupBox.setLayout(snap_channel_groupBox_layout)
        self.main_tab_layout.addWidget(snap_channel_groupBox, 1, 0)

        # exposure in snap_live_tab
        self.exposure_widget = DefaultCameraExposureWidget()
        exp_groupBox = QtW.QGroupBox()
        exp_groupBox.setSizePolicy(wdg_sizepolicy)
        exp_groupBox.setTitle("Exposure Time")
        exp_groupBox_layout = QtW.QHBoxLayout()
        exp_groupBox_layout.setContentsMargins(5, 5, 5, 5)
        exp_groupBox_layout.addWidget(self.exposure_widget)
        exp_groupBox.setLayout(exp_groupBox_layout)
        self.main_tab_layout.addWidget(exp_groupBox, 1, 1)

        # snap/live
        wdg = QtW.QGroupBox()
        wdg_layout = QtW.QVBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(5, 5, 5, 5)
        wdg.setLayout(wdg_layout)
        self.btn_wdg = QtW.QWidget()
        btn_wdg_layout = QtW.QHBoxLayout()
        self.snap_Button = SnapButton()
        self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
        btn_wdg_layout.addWidget(self.snap_Button)
        self.live_Button = LiveButton()
        self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
        btn_wdg_layout.addWidget(self.live_Button)
        self.btn_wdg.setLayout(btn_wdg_layout)
        wdg_layout.addWidget(self.btn_wdg)
        self.main_tab_layout.addWidget(wdg, 2, 0, 1, 2)

        # max min in snap_live_tab
        max_min_wdg = QtW.QGroupBox()
        max_min_wdg_layout = QtW.QHBoxLayout()
        max_min_wdg_layout.setContentsMargins(5, 5, 5, 5)
        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        self.max_min_val_label = QtW.QLabel()
        max_min_wdg_layout.addWidget(self.max_min_val_label_name)
        max_min_wdg_layout.addWidget(self.max_min_val_label)
        max_min_wdg.setLayout(max_min_wdg_layout)
        wdg_layout.addWidget(max_min_wdg)
        self.main_tab_layout.addWidget(max_min_wdg, 3, 0, 1, 2)

        # add illumination
        ill_group = QtW.QGroupBox()
        ill_group.setTitle("Illumination")
        ill_group_layout = QtW.QVBoxLayout()
        ill_group_layout.setSpacing(0)
        ill_group_layout.setContentsMargins(5, 10, 5, 10)
        ill_group.setLayout(ill_group_layout)
        self.ill = IlluminationWidget()
        ill_group_layout.addWidget(self.ill)
        self.main_tab_layout.addWidget(ill_group, 4, 0, 1, 2)

        # add camera
        cam_group = QtW.QGroupBox()
        cam_group.setTitle("Camera ROI")
        cam_group_layout = QtW.QVBoxLayout()
        cam_group_layout.setSpacing(0)
        cam_group_layout.setContentsMargins(5, 10, 5, 10)
        cam_group.setLayout(cam_group_layout)
        self.cam_wdg = CameraRoiWidget()
        cam_group_layout.addWidget(self.cam_wdg)
        self.main_tab_layout.addWidget(cam_group, 5, 0, 1, 2)

        # spacer
        spacer = QtW.QSpacerItem(
            20, 40, QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Expanding
        )
        self.main_tab_layout.addItem(spacer, 6, 0)

        # add tabWidget
        self.tabWidget.setLayout(self.tabWidget_layout)
        self.tabWidget.addTab(self.main_tab, "Main")
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
