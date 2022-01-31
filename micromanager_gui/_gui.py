from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

from .explore_sample import ExploreSample
from .multid_widget import MultiDWidget

if TYPE_CHECKING:
    import napari.viewer


ICONS = Path(__file__).parent / "icons"


class MMConfigurationWidget(QtW.QWidget):

    MM_CONFIG = str(Path(__file__).parent / "_ui" / "mm_configuration.ui")

    # The MM_CONFIG above contains these objects:
    mm_config_groupBox: QtW.QGroupBox
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cfg_Button: QtW.QPushButton
    properties_Button: QtW.QPushButton

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_CONFIG, self)


class MMObjectivesWidget(QtW.QWidget):

    MM_OBJ = str(Path(__file__).parent / "_ui" / "mm_objectives.ui")

    # The MM_OBJ above contains these objects:
    objective_groupBox: QtW.QGroupBox
    objective_comboBox: QtW.QComboBox

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_OBJ, self)


class MMIlluminationWidget(QtW.QWidget):

    MM_ILL = str(Path(__file__).parent / "_ui" / "mm_illumination.ui")

    # The MM_ILL above contains these objects:
    illumination_groupBox: QtW.QGroupBox
    illumination_Button: QtW.QPushButton

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_ILL, self)


class MMCameraWidget(QtW.QWidget):

    MM_CAM = str(Path(__file__).parent / "_ui" / "mm_camera.ui")

    # The MM_CAM above contains these objects:
    camera_groupBox: QtW.QGroupBox
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox
    px_size_doubleSpinBox: QtW.QDoubleSpinBox
    cam_roi_comboBox: QtW.QComboBox
    crop_Button: QtW.QPushButton

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_CAM, self)


class MMStagesWidget(QtW.QWidget):

    MM_XYZ_STAGE = str(Path(__file__).parent / "_ui" / "mm_xyz_stage.ui")

    # The MM_XYZ_STAGE above contains these objects:
    stage_groupBox: QtW.QGroupBox

    XY_groupBox: QtW.QGroupBox
    xy_device_comboBox: QtW.QComboBox
    xy_step_size_SpinBox: QtW.QSpinBox
    y_up_Button: QtW.QPushButton
    y_down_Button: QtW.QPushButton
    left_Button: QtW.QPushButton
    right_Button: QtW.QPushButton

    Z_groupBox: QtW.QGroupBox
    z_step_size_doubleSpinBox: QtW.QDoubleSpinBox
    focus_device_comboBox: QtW.QComboBox
    up_Button: QtW.QPushButton
    down_Button: QtW.QPushButton

    offset_Z_groupBox: QtW.QGroupBox
    offset_device_comboBox: QtW.QComboBox
    offset_z_step_size_doubleSpinBox: QtW.QDoubleSpinBox
    offset_up_Button: QtW.QPushButton
    offset_down_Button: QtW.QPushButton

    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit

    snap_on_click_checkBox: QtW.QCheckBox

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_XYZ_STAGE, self)

        # button icons
        for attr, icon in [
            ("left_Button", "left_arrow_1_green.svg"),
            ("right_Button", "right_arrow_1_green.svg"),
            ("y_up_Button", "up_arrow_1_green.svg"),
            ("y_down_Button", "down_arrow_1_green.svg"),
            ("up_Button", "up_arrow_1_green.svg"),
            ("down_Button", "down_arrow_1_green.svg"),
            ("offset_up_Button", "up_arrow_1_green.svg"),
            ("offset_down_Button", "down_arrow_1_green.svg"),
        ]:
            btn = getattr(self, attr)
            btn.setIcon(QIcon(str(ICONS / icon)))
            btn.setIconSize(QSize(30, 30))


class MMTabWidget(QtW.QWidget):

    MM_TAB = str(Path(__file__).parent / "_ui" / "mm_snap_and_tabs.ui")

    # The MM_TAB above contains these objects:
    tabWidget: QtW.QTabWidget

    snap_live_tab: QtW.QWidget

    snap_channel_groupBox: QtW.QGroupBox
    snap_channel_comboBox: QtW.QComboBox

    exp_groupBox: QtW.QGroupBox
    exp_spinBox: QtW.QDoubleSpinBox

    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton

    max_min_val_label: QtW.QLabel

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(self.MM_TAB, self)

        # button icons
        for attr, icon in [
            ("snap_Button", "cam.svg"),
            ("live_Button", "vcam.svg"),
        ]:
            btn = getattr(self, attr)
            btn.setIcon(QIcon(str(ICONS / icon)))
            btn.setIconSize(QSize(30, 30))


class MicroManagerWidget(QtW.QWidget):

    MAIN_UI = str(Path(__file__).parent / "_ui" / "micromanager_gui.ui")

    def __init__(self, viewer: napari.viewer.Viewer, remote=True):
        super().__init__()

        uic.loadUi(self.MAIN_UI, self)

        self.viewer = viewer
        self._mmcore = RemoteMMCore() if remote else CMMCorePlus()

        # add sub_widgets
        self.mm_configuration = MMConfigurationWidget()
        self.mm_objectives = MMObjectivesWidget()
        self.mm_illumination = MMIlluminationWidget()
        self.mm_camera = MMCameraWidget()
        self.mm_xyz_stages = MMStagesWidget()

        self.mm_tab = MMTabWidget()
        # add mda and explorer tabs to mm_tab widget
        self.mm_mda = MultiDWidget(self._mmcore)
        self.mm_explorer = ExploreSample(self.viewer, self._mmcore)
        self.mm_tab.tabWidget.addTab(self.mm_mda, "Multi-D Acquisition")
        self.mm_tab.tabWidget.addTab(self.mm_explorer, "Sample Explorer")

    def create_gui(self):

        # main widget
        self.main_layout = QtW.QGridLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # add all widgets to main_layout
        self.main_layout.addWidget(self.mm_configuration, 0, 0)
        self.add_mm_objectives_illumination_camera_widget()
        self.main_layout.addWidget(self.mm_xyz_stages, 2, 0)
        self.main_layout.addWidget(self.mm_tab, 3, 0)

        # set main_layout layout
        self.setLayout(self.main_layout)

        self.mm_configuration.cfg_LineEdit.setText("load a micromanager .cfg file")

    def add_mm_objectives_illumination_camera_widget(self):

        # main objectives, illumination and camera widget
        wdg_1 = QtW.QWidget()
        wdg_1_layout = QtW.QGridLayout()
        wdg_1_layout.setContentsMargins(0, 0, 0, 0)
        wdg_1_layout.setSpacing(0)

        # create objectives and illumination widget
        wdg_2 = QtW.QWidget()
        wdg_2_layout = QtW.QGridLayout()
        wdg_2_layout.setContentsMargins(0, 0, 0, 0)
        wdg_2_layout.setSpacing(0)
        wdg_2_layout.addWidget(self.mm_objectives, 0, 0)
        wdg_2_layout.addWidget(self.mm_illumination, 1, 0)
        # set layout wdg_2
        wdg_2.setLayout(wdg_2_layout)

        # add objectives and illumination widgets to wdg 1
        wdg_1_layout.addWidget(wdg_2, 0, 0)

        # add camera widget to wdg 1
        wdg_1_layout.addWidget(self.mm_camera, 0, 1)

        # set layout wdg_1
        wdg_1.setLayout(wdg_1_layout)

        # add wdg_1 to main_layout
        self.main_layout.addWidget(wdg_1, 1, 0)
