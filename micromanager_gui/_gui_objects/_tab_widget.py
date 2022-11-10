from pathlib import Path

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

from ._illumination_widget import IlluminationWidget

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
        self.main_layout.setContentsMargins(0, 10, 0, 0)

        # tabWidget
        self.tabWidget = QtW.QTabWidget()
        self.tabWidget.setMovable(True)
        self.tabWidget_layout = QtW.QVBoxLayout()

        self.tabWidget.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding)
        )

        # snap_live_tab and layout
        self.main_tab = QtW.QWidget()
        self.main_tab_layout = QtW.QGridLayout()

        # channel in snap_live_tab
        snap_channel_groupBox = self._add_channel_group()
        self.main_tab_layout.addWidget(snap_channel_groupBox, 0, 0)

        # exposure in snap_live_tab
        exp_groupBox = self._add_exposure_group()
        self.main_tab_layout.addWidget(exp_groupBox, 0, 1)

        # snap/live in snap_live_tab
        btn_wdg = self._add_snap_live_buttons()
        self.main_tab_layout.addWidget(btn_wdg, 1, 0, 1, 2)

        # max min in snap_live_tab
        max_min_wdg = self._add_min_max()
        self.main_tab_layout.addWidget(max_min_wdg, 2, 0, 1, 2)

        # objectives
        obj = self._add_objectives_wdg()
        self.main_tab_layout.addWidget(obj, 3, 0, 1, 2)

        # illumination wdg
        self.ill = IlluminationWidget()
        self.main_tab_layout.addWidget(self.ill, 4, 0, 1, 2)

        # camera
        cam_coll = self._add_camera_collaplible()
        self.main_tab_layout.addWidget(cam_coll, 5, 0, 1, 2)

        # spacer
        spacer = QtW.QSpacerItem(
            20, 40, QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Expanding
        )
        self.main_tab_layout.addItem(spacer, 6, 0)

        # set snap_live_tab layout
        self.main_tab.setLayout(self.main_tab_layout)

        # add tabWidget
        self.tabWidget.setLayout(self.tabWidget_layout)
        self.tabWidget.addTab(self.main_tab, "Main")
        self.main_layout.addWidget(self.tabWidget)

        # Set main layout
        self.setLayout(self.main_layout)

    def _add_channel_group(self):
        snap_channel_groupBox = QtW.QGroupBox()
        snap_channel_groupBox.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        )
        snap_channel_groupBox.setTitle("Channel")
        snap_channel_groupBox_layout = QtW.QHBoxLayout()
        snap_channel_groupBox_layout.setContentsMargins(5, 5, 5, 5)
        self.snap_channel_comboBox = ChannelWidget()
        snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
        snap_channel_groupBox.setLayout(snap_channel_groupBox_layout)
        return snap_channel_groupBox

    def _add_exposure_group(self):
        self.exposure_widget = DefaultCameraExposureWidget()
        exp_groupBox = QtW.QGroupBox()
        exp_groupBox.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        )
        exp_groupBox.setTitle("Exposure Time")
        exp_groupBox_layout = QtW.QHBoxLayout()
        exp_groupBox_layout.setContentsMargins(5, 5, 5, 5)
        exp_groupBox_layout.addWidget(self.exposure_widget)
        exp_groupBox.setLayout(exp_groupBox_layout)
        return exp_groupBox

    def _add_snap_live_buttons(self):
        btn_wdg = QtW.QWidget()
        btn_wdg.setMaximumHeight(65)
        btn_wdg_layout = QtW.QHBoxLayout()
        self.snap_Button = SnapButton()
        self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
        btn_wdg_layout.addWidget(self.snap_Button)
        self.live_Button = LiveButton()
        self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
        self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
        btn_wdg_layout.addWidget(self.live_Button)
        btn_wdg.setLayout(btn_wdg_layout)
        return btn_wdg

    def _add_min_max(self):
        max_min_wdg = QtW.QGroupBox()
        max_min_wdg_layout = QtW.QHBoxLayout()
        max_min_wdg_layout.setContentsMargins(5, 3, 5, 3)
        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        self.max_min_val_label = QtW.QLabel()
        max_min_wdg_layout.addWidget(self.max_min_val_label_name)
        max_min_wdg_layout.addWidget(self.max_min_val_label)
        max_min_wdg.setLayout(max_min_wdg_layout)
        return max_min_wdg

    def _add_objectives_wdg(self):
        self.obj_wdg = ObjectivesWidget()
        obj_wdg = QtW.QGroupBox()
        obj_wdg_layout = QtW.QHBoxLayout()
        obj_wdg_layout.setContentsMargins(5, 5, 5, 5)
        obj_wdg_layout.setSpacing(7)
        obj_wdg_layout.addWidget(self.obj_wdg)
        obj_wdg.setLayout(obj_wdg_layout)
        return obj_wdg

    def _add_camera_collaplible(self):
        self.cam_wdg = CameraRoiWidget()
        cam_group = QtW.QGroupBox(title="Camera ROI")
        cam_layout = QtW.QVBoxLayout()
        cam_layout.setSpacing(0)
        cam_layout.setContentsMargins(5, 5, 5, 5)
        cam_group.setLayout(cam_layout)
        cam_layout.addWidget(self.cam_wdg)
        return cam_group
