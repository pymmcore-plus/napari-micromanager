from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, RemoteMMCore
from qtpy import QtCore
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
    """
    contains the following objects:
    - cfg_groupBox: QtW.QGroupBox
    - cfg_LineEdit: QtW.QLineEdit
    - browse_cfg_Button: QtW.QPushButton
    - load_cfg_Button: QtW.QPushButton
    - properties_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # cfg groupbox in widget
        self.cfg_groupBox = QtW.QGroupBox()
        self.cfg_groupBox.setTitle("Camera")
        self.main_layout.addWidget(self.cfg_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # define camera_groupBox layout
        self.cfg_groupBox_layout = QtW.QGridLayout()

        # add to cfg_groupBox layout:
        self.cfg_LineEdit = QtW.QLineEdit()
        self.browse_cfg_Button = QtW.QPushButton(text="...")
        self.load_cfg_Button = QtW.QPushButton(text="Load")
        self.properties_Button = QtW.QPushButton(text="Prop")
        # widgets in in cfg_groupBox layout
        self.cfg_groupBox_layout.addWidget(self.cfg_LineEdit, 0, 0)
        self.cfg_groupBox_layout.addWidget(self.browse_cfg_Button, 0, 1)
        self.cfg_groupBox_layout.addWidget(self.load_cfg_Button, 0, 2)
        self.cfg_groupBox_layout.addWidget(self.properties_Button, 0, 3)
        # set cfg_groupBox layout
        self.cfg_groupBox.setLayout(self.cfg_groupBox_layout)


class MMObjectivesWidget(QtW.QWidget):
    """
    contains the following objects:
    - objective_groupBox: QtW.QGroupBox
    - objective_comboBox: QtW.QLineEdit
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()

        # groupbox in widget
        self.objective_groupBox = QtW.QGroupBox()
        self.objective_groupBox.setTitle("Objectives")
        self.main_layout.addWidget(self.objective_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # combobox in groupbox
        self.objective_groupBox_layout = QtW.QGridLayout()

        self.objective_comboBox = QtW.QComboBox()
        self.objective_groupBox.setMinimumSize(QtCore.QSize(160, 0))
        # self.objective_groupBox.setObjectName("objective_groupBox")

        self.objective_groupBox_layout.addWidget(self.objective_comboBox, 0, 0)
        self.objective_groupBox.setLayout(self.objective_groupBox_layout)


class MMIlluminationWidget(QtW.QWidget):
    """
    contains the following objects:
    - illumination_groupBox: QtW.QGroupBox
    - illumination_Button: QtW.QLineEdit
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # groupbox in widget
        self.illumination_groupBox = QtW.QGroupBox()
        self.illumination_groupBox.setTitle("Illumination")
        self.main_layout.addWidget(self.illumination_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # PushButton in groupbox
        self.illumination_groupBox_layout = QtW.QGridLayout()
        self.illumination_Button = QtW.QPushButton(text="Illumination")
        self.illumination_groupBox.setMinimumSize(QtCore.QSize(160, 0))

        self.illumination_groupBox_layout.addWidget(self.illumination_Button, 0, 0)
        self.illumination_groupBox.setLayout(self.illumination_groupBox_layout)


class MMCameraWidget(QtW.QWidget):
    """
    contains the following objects:
    - camera_groupBox: QtW.QGroupBox
    - bin_comboBox: QtW.QComboBox
    - bit_comboBox: QtW.QComboBox
    - px_size_doubleSpinBox: QtW.QDoubleSpinBox
    - cam_roi_comboBox: QtW.QComboBox
    - crop_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # camera groupbox in widget
        self.camera_groupBox = QtW.QGroupBox()
        self.camera_groupBox.setTitle("Camera")
        self.main_layout.addWidget(self.camera_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # define camera_groupBox layout
        self.camera_groupBox_layout = QtW.QGridLayout()

        # add to camera_groupBox layout:
        # bin widget and layout
        self.bin_wdg = QtW.QWidget()
        self.bin_layout = QtW.QGridLayout()
        # label bin in layout
        self.bin_label = QtW.QLabel(text="Binning:")
        self.bin_label.setMaximumWidth(65)
        self.bin_layout.addWidget(self.bin_label, 0, 0)
        # combobox bin in layout
        self.bin_comboBox = QtW.QComboBox()
        # self.bin_comboBox.setMaximumWidth(75)
        self.bin_layout.addWidget(self.bin_comboBox, 0, 1)
        # set bin_wdg layout
        self.bin_wdg.setLayout(self.bin_layout)
        # bin widget in groupbox
        self.camera_groupBox_layout.addWidget(self.bin_wdg, 0, 0)

        # bit widget and layout
        self.bit_wdg = QtW.QWidget()
        self.bit_layout = QtW.QGridLayout()
        # label bit in groupbox r1 c0
        self.bit_label = QtW.QLabel(text="Bit Depth:")
        self.bit_label.setMaximumWidth(65)
        self.bit_layout.addWidget(self.bit_label, 0, 0)
        # combobox bit in groupbox r1 c1
        self.bit_comboBox = QtW.QComboBox()
        # self.bit_comboBox.setMaximumWidth(75)
        self.bit_layout.addWidget(self.bit_comboBox, 0, 1)
        # set bit_wdg layout
        self.bit_wdg.setLayout(self.bit_layout)
        # bit widget in groupbox
        self.camera_groupBox_layout.addWidget(self.bit_wdg, 1, 0)

        # cam_px widget and layout
        self.cam_px_wdg = QtW.QWidget()
        self.cam_px_layout = QtW.QGridLayout()
        # label px in groupbox r0 c2
        self.cam_px_label = QtW.QLabel(text="Pixel (µm):")
        self.cam_px_label.setMaximumWidth(70)
        self.cam_px_layout.addWidget(self.cam_px_label, 0, 0)
        # doublespinbox px in groupbox r0 c3
        self.px_size_doubleSpinBox = QtW.QDoubleSpinBox()
        # self.px_size_doubleSpinBox.setMaximumWidth(120)
        self.cam_px_layout.addWidget(self.px_size_doubleSpinBox, 0, 1)
        # set bit_wdg layout
        self.cam_px_wdg.setLayout(self.cam_px_layout)
        # bit widget in groupbox
        self.camera_groupBox_layout.addWidget(self.cam_px_wdg, 0, 1)

        # camera roi widget and layout
        self.cam_roi_wdg = QtW.QWidget()
        self.cam_roi_wdg_layout = QtW.QGridLayout()
        # camera roi label in cam_roi_wdg
        self.cam_roi_label = QtW.QLabel(text="ROI:")
        self.cam_roi_label.setMaximumWidth(30)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_label, 0, 0)
        # combobox in cam_roi_wdg
        self.cam_roi_comboBox = QtW.QComboBox()
        self.cam_roi_comboBox.setMinimumWidth(70)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_comboBox, 0, 1)
        # pushbutton in cam_roi_wdg
        self.crop_Button = QtW.QPushButton(text="Crop")
        self.crop_Button.setMaximumWidth(50)
        self.cam_roi_wdg_layout.addWidget(self.crop_Button, 0, 2)
        # set cam_roi_wdg layout
        self.cam_roi_wdg.setLayout(self.cam_roi_wdg_layout)
        # cam_roi widget in groupbox
        self.camera_groupBox_layout.addWidget(self.cam_roi_wdg, 1, 1)

        # set layout camera_groupBox
        self.camera_groupBox.setLayout(self.camera_groupBox_layout)


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
