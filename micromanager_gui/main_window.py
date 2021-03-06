import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtW
from PyQt5.QtGui import QIcon
from qtpy import uic
from qtpy.QtWidgets import QFileDialog, QGridLayout

from .explore_sample import ExploreSample
from .mmcore_pymmcore import MMCore
from .multid_widget import MultiDWidget

if TYPE_CHECKING:
    import napari

# dir_path = Path(__file__).parent
icon_path = Path(__file__).parent / "icons"

UI_FILE = str(Path(__file__).parent / "micromanager_gui.ui")
DEFAULT_CFG_FILE = str(
    (Path(__file__).parent / "demo_config.cfg").absolute()
)  # look for the 'demo_config.cfg' in the parent folder
DEFAULT_CFG_NAME = "demo.cfg"

mmcore = MMCore()


class MainWindow(QtW.QMainWindow):
    # The UI_FILE above contains these objects:
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cgf_Button: QtW.QPushButton

    objective_groupBox: QtW.QGroupBox
    objective_comboBox: QtW.QComboBox

    camera_groupBox: QtW.QGroupBox
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox

    position_groupBox: QtW.QGroupBox
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit

    stage_groupBox: QtW.QGroupBox
    XY_groupBox: QtW.QGroupBox
    Z_groupBox: QtW.QGroupBox
    left_Button: QtW.QPushButton
    right_Button: QtW.QPushButton
    y_up_Button: QtW.QPushButton
    y_down_Button: QtW.QPushButton
    up_Button: QtW.QPushButton
    down_Button: QtW.QPushButton
    xy_step_size_SpinBox: QtW.QSpinBox
    z_step_size_doubleSpinBox: QtW.QDoubleSpinBox

    tabWidget: QtW.QTabWidget
    snap_live_tab: QtW.QWidget
    multid_tab: QtW.QWidget

    snap_channel_groupBox: QtW.QGroupBox
    snap_channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton

    max_val_lineEdit: QtW.QLineEdit
    min_val_lineEdit: QtW.QLineEdit

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()

        self.viewer = viewer
        self.worker = None

        uic.loadUi(UI_FILE, self)  # load QtDesigner .ui file

        self.cfg_LineEdit.setText(
            DEFAULT_CFG_NAME
        )  # fill cfg line with DEFAULT_CFG_NAME ('demo.cfg')

        self.obj_mag = []
        self.is_true = False  # self.get_explorer_info()
        self.magnification = None

        # ________________________________________________________________________
        # create MultiDWidget() widgets
        self.mda = MultiDWidget()
        self.explorer = ExploreSample()

        # create QWidget() to be added to the main tabWidget
        self.multid_tab = QtW.QWidget()
        self.explorer_tab = QtW.QWidget()

        # add tabs
        self.tabWidget.addTab(self.multid_tab, "Multi-D Acquisition")
        self.tabWidget.addTab(self.explorer_tab, "Sample Explorer")

        # create tabs layout and add the widgets
        self.multid_tab.layout = QGridLayout()
        self.multid_tab.layout.addWidget(self.mda)
        self.multid_tab.setLayout(self.multid_tab.layout)

        self.explorer_tab.layout = QGridLayout()
        self.explorer_tab.layout.addWidget(self.explorer)
        self.explorer_tab.setLayout(self.explorer_tab.layout)
        # ________________________________________________________________________

        # connect buttons
        self.load_cgf_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)

        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)

        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        # button's icon
        # arrows icons
        # self.left_Button.setIcon(QIcon(str(icon_path/'left_arrow_1.svg')))
        self.left_Button.setIcon(QIcon(str(icon_path / "left_arrow_1_green.svg")))
        self.left_Button.setIconSize(QtCore.QSize(30, 30))
        # self.right_Button.setIcon(QIcon(str(icon_path/'right_arrow_1.svg')))
        self.right_Button.setIcon(QIcon(str(icon_path / "right_arrow_1_green.svg")))
        self.right_Button.setIconSize(QtCore.QSize(30, 30))
        # self.y_up_Button.setIcon(QIcon(str(icon_path/'up_arrow_1.svg')))
        self.y_up_Button.setIcon(QIcon(str(icon_path / "up_arrow_1_green.svg")))
        self.y_up_Button.setIconSize(QtCore.QSize(30, 30))
        # self.y_down_Button.setIcon(QIcon(str(icon_path/'down_arrow_1.svg')))
        self.y_down_Button.setIcon(QIcon(str(icon_path / "down_arrow_1_green.svg")))
        self.y_down_Button.setIconSize(QtCore.QSize(30, 30))

        # self.up_Button.setIcon(QIcon(str(icon_path/'up_arrow.svg')))
        self.up_Button.setIcon(QIcon(str(icon_path / "up_arrow_1_green.svg")))
        self.up_Button.setIconSize(QtCore.QSize(30, 30))
        # self.down_Button.setIcon(QIcon(str(icon_path/'down_arrow.svg')))
        self.down_Button.setIcon(QIcon(str(icon_path / "down_arrow_1_green.svg")))
        self.down_Button.setIconSize(QtCore.QSize(30, 30))

        # snap/live icons
        self.snap_Button.setIcon(QIcon(str(icon_path / "cam.svg")))
        self.snap_Button.setIconSize(QtCore.QSize(30, 30))
        self.live_Button.setIcon(QIcon(str(icon_path / "vcam.svg")))
        self.live_Button.setIconSize(QtCore.QSize(40, 40))

        # connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)

        # connect callback
        mmcore.xy_stage_position_changed.connect(self.update_stage_position_xy)
        mmcore.stage_position_changed.connect(self.update_stage_position_z)

        # connect the Signal____________________________________________________________
        # self.mda.new_frame.connect(self.add_frame_multid)

        self.explorer.new_frame.connect(self.add_frame_explorer)
        self.explorer.delete_snaps.connect(self.delete_layer)
        self.explorer.send_explorer_info.connect(self.get_explorer_info)
        self.explorer.delete_previous_scan.connect(self.delete_layer)

        # self.mda.empty_stack_to_viewer.connect(self.add_empty_stack_mda)
        mmcore.stack_to_viewer.connect(self.add_stack_mda)

        # ________________________________________________________________________

    # SIGNAL________________________________________________________________________

    # explor_sample.py
    def get_explorer_info(self, shape_stitched_x, shape_stitched_y):

        # Get coordinates mouse_drag_callbacks
        @self.viewer.mouse_drag_callbacks.append  # is it possible to double click?
        def get_event_add(viewer, event):
            try:
                for i in self.viewer.layers:
                    selected_layer = self.viewer.layers.selected
                    if "stitched_" in str(i) and "stitched_" in str(selected_layer):
                        layer = self.viewer.layers[str(i)]
                        coord = layer.coordinates
                        # self.is_true = True
                        # print(f'\ncoordinates: x={coord[1]}, y={coord[0]}')
                        coord_x = coord[1]
                        coord_y = coord[0]
                        if coord_x <= shape_stitched_x and coord_y < shape_stitched_y:
                            if coord_x > 0 and coord_y > 0:
                                self.explorer.x_lineEdit.setText(str(round(coord_x)))
                                self.explorer.y_lineEdit.setText(str(round(coord_y)))
                                break

                            else:
                                self.explorer.x_lineEdit.setText("None")
                                self.explorer.y_lineEdit.setText("None")
                        else:
                            self.explorer.x_lineEdit.setText("None")
                            self.explorer.y_lineEdit.setText("None")
            except KeyError:
                pass

    def delete_layer(self, name):
        layer_set = set()
        for layer in self.viewer.layers:
            layer_set.add(str(layer))
        if name in layer_set:
            self.viewer.layers.remove(name)
        layer_set.clear()

    def add_frame_explorer(self, name, array):
        layer_name = name
        try:
            layer = self.viewer.layers[layer_name]
            layer.data = array
        except KeyError:
            self.viewer.add_image(array, name=layer_name)

    # mmcore_pymmcore.py
    def add_stack_mda(
        self, stack, cnt, xy_pos
    ):  # TO DO: add the file name form the save box
        print("STACK SENT...")
        name = f"Exp{cnt}_Pos{xy_pos}"
        try:
            layer = self.viewer.layers[name]
            layer.data = stack
        except KeyError:
            self.viewer.add_image(stack, name=name)

    # ________________________________________________________________________

    def get_devices_and_props(self):
        # List devices and properties that you can set
        devices = mmcore.getLoadedDevices()
        print("\nDevice status:__________________________")
        for i in range(len(devices)):
            device = devices[i]
            properties = mmcore.getDevicePropertyNames(device)
            for p in range(len(properties)):
                prop = properties[p]
                values = mmcore.getAllowedPropertyValues(device, prop)
                print(
                    f"Device: {str(device)}  Property: {str(prop)} Value: {str(values)}"
                )
        print("________________________________________")

    def get_groups_list(self):
        group = []
        for groupName in mmcore.getAvailableConfigGroups():
            print(f"*********\nGroup_Name: {str(groupName)}")
            for configName in mmcore.getAvailableConfigs(groupName):
                group.append(configName)
                print(f"Config_Name: {str(configName)}")
                props = str(mmcore.getConfigData(groupName, configName).getVerbose())
                print(f"Properties: {props}")
            print("*********")

    def browse_cfg(self):
        mmcore.unloadAllDevices()  # unload all devicies
        print(f"Loaded Devicies: {mmcore.getLoadedDevices()}")

        # clear spinbox/combobox
        self.objective_comboBox.clear()
        self.bin_comboBox.clear()
        self.bit_comboBox.clear()
        self.snap_channel_comboBox.clear()

        file_dir = QFileDialog.getOpenFileName(self, "", "⁩", "cfg(*.cfg)")
        self.new_cfg_file = file_dir[0]
        cfg_name = os.path.basename(str(self.new_cfg_file))
        self.cfg_LineEdit.setText(str(cfg_name))
        self.setEnabled(False)
        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")
        self.load_cgf_Button.setEnabled(True)

    def load_cfg(self):

        self.obj_mag.clear()

        self.setEnabled(True)

        self.load_cgf_Button.setEnabled(False)

        cfg_file = self.cfg_LineEdit.text()
        if cfg_file == DEFAULT_CFG_NAME:
            self.new_cfg_file = DEFAULT_CFG_FILE

        try:
            mmcore.loadSystemConfiguration(
                self.new_cfg_file
            )  # load the configuration file
            print(f"Loaded Devicies: {mmcore.getLoadedDevices()}")
        except KeyError:
            print("Select a valid .cfg file.")

        self.get_devices_and_props()
        self.get_groups_list()

        # Get Camera Options
        self.cam_device = mmcore.getCameraDevice()
        cam_props = mmcore.getDevicePropertyNames(self.cam_device)
        #        print(cam_props)
        if "Binning" in cam_props:
            bin_opts = mmcore.getAllowedPropertyValues(self.cam_device, "Binning")
            self.bin_comboBox.addItems(bin_opts)
            self.bin_comboBox.setCurrentText(
                mmcore.getProperty(self.cam_device, "Binning")
            )
            mmcore.setProperty(self.cam_device, "Binning", "1")

        if "PixelType" in cam_props:
            px_t = mmcore.getAllowedPropertyValues(self.cam_device, "PixelType")
            self.bit_comboBox.addItems(px_t)
            if "16" in px_t:
                self.bit_comboBox.setCurrentText("16bit")
                mmcore.setProperty(self.cam_device, "PixelType", "16bit")

        # Get Objective Options
        if "Objective" in mmcore.getLoadedDevices():
            mmcore.setPosition("Z_Stage", 0)
            obj_opts = mmcore.getStateLabels("Objective")

            self.objective_comboBox.addItems(obj_opts)
            self.objective_comboBox.setCurrentText(obj_opts[5])

            # obj_curr_pos = mmcore.getState("Objective")
            # print(f'Objective Nosepiece Position: {obj_curr_pos}')

        # Get Channel List
        if "Channel" in mmcore.getAvailableConfigGroups():
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.snap_channel_comboBox.addItems(channel_list)
            self.explorer.scan_channel_comboBox.addItems(channel_list)
        else:
            print("Could not find 'Channel' in the ConfigGroups")

        self.update_stage_position_xy()
        self.update_stage_position_z()

        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")

    # set (and print) properties when value/string change
    # def cam_changed(self):
    def bit_changed(self):
        if self.bit_comboBox.count() > 0:
            mmcore.setProperty(
                self.cam_device, "PixelType", self.bit_comboBox.currentText()
            )
            pixel_type = mmcore.getProperty(mmcore.getCameraDevice(), "PixelType")
            print(f"PixelType: {pixel_type}")

    def bin_changed(self):
        if self.bin_comboBox.count() > 0:
            mmcore.setProperty(
                self.cam_device, "Binning", self.bin_comboBox.currentText()
            )
            print(f'Binning: {mmcore.getProperty(mmcore.getCameraDevice(), "Binning")}')

    def update_stage_position_xy(self):
        x = int(mmcore.getXPosition())
        y = int(mmcore.getYPosition())
        z = int(mmcore.getPosition("Z_Stage"))
        self.x_lineEdit.setText(str("%.0f" % x))
        self.y_lineEdit.setText(str("%.0f" % y))
        self.z_lineEdit.setText(str("%.1f" % z))
        # print(f'XY Stage moved to x:{x} y:{y} (z:{z})')

    def update_stage_position_z(self):
        x = int(mmcore.getXPosition())
        y = int(mmcore.getYPosition())
        z = int(mmcore.getPosition("Z_Stage"))
        self.x_lineEdit.setText(str("%.0f" % x))
        self.y_lineEdit.setText(str("%.0f" % y))
        self.z_lineEdit.setText(str("%.1f" % z))
        # print(f'Z Stage moved to z:{z} (x:{x} y:{y})')

    def stage_x_left(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition((xpos + (-val)), ypos)
        x_new = int(mmcore.getXPosition())
        self.x_lineEdit.setText(str("%.0f" % x_new))
        mmcore.waitForDevice("XY_Stage")

    def stage_x_right(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition((xpos + val), ypos)
        x_new = int(mmcore.getXPosition())
        self.x_lineEdit.setText(str("%.0f" % x_new))
        mmcore.waitForDevice("XY_Stage")

    def stage_y_up(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition(xpos, (ypos + val))
        y_new = int(mmcore.getYPosition())
        self.y_lineEdit.setText(str("%.0f" % y_new))
        mmcore.waitForDevice("XY_Stage")

    def stage_y_down(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition(xpos, (ypos + (-val)))
        y_new = int(mmcore.getYPosition())
        self.y_lineEdit.setText(str("%.0f" % y_new))
        mmcore.waitForDevice("XY_Stage")

    def stage_z_up(self):
        zpos = mmcore.getPosition("Z_Stage")
        z_val = float(self.z_step_size_doubleSpinBox.value())
        mmcore.setPosition("Z_Stage", zpos + z_val)
        z_new = float(mmcore.getPosition("Z_Stage"))
        self.z_lineEdit.setText(str("%.1f" % z_new))
        mmcore.waitForDevice("Z_Stage")

    def stage_z_down(self):
        zpos = mmcore.getPosition("Z_Stage")
        z_val = float(self.z_step_size_doubleSpinBox.value())
        mmcore.setPosition("Z_Stage", zpos + (-z_val))
        z_new = float(mmcore.getPosition("Z_Stage"))
        self.z_lineEdit.setText(str("%.1f" % z_new))
        mmcore.waitForDevice("Z_Stage")

    def change_objective(self):
        if self.objective_comboBox.count() > 0:
            print("\nchanging objective...")
            currentZ = mmcore.getPosition("Z_Stage")
            print(f"currentZ: {currentZ}")
            mmcore.setPosition("Z_Stage", 0)  # set low z position
            mmcore.waitForDevice("Z_Stage")
            print(self.objective_comboBox.currentText())
            mmcore.setProperty(
                "Objective", "Label", self.objective_comboBox.currentText()
            )
            mmcore.waitForDevice("Objective")
            print(f"downpos: {mmcore.getPosition('Z_Stage')}")
            mmcore.setPosition("Z_Stage", currentZ)
            mmcore.waitForDevice("Z_Stage")
            print(f"upagain: {mmcore.getPosition('Z_Stage')}")
            print(f"OBJECTIVE: {mmcore.getProperty('Objective', 'Label')}")

            # define and set pixel size Config
            mmcore.deletePixelSizeConfig(mmcore.getCurrentPixelSizeConfig())
            curr_obj_name = mmcore.getProperty("Objective", "Label")
            mmcore.definePixelSizeConfig(curr_obj_name)
            mmcore.setPixelSizeConfig(curr_obj_name)
            print(f"Current pixel cfg: {mmcore.getCurrentPixelSizeConfig()}")

            # get magnification info from the objective
            for i in range(len(curr_obj_name)):
                character = curr_obj_name[i]
                if character == "X" or character == "x":
                    if i <= 3:
                        magnification_string = curr_obj_name[:i]
                        self.magnification = int(magnification_string)
                        print(f"Current Magnification: {self.magnification}X")
                    else:
                        self.magnification = None
                        print(
                            "MAGNIFICATION NOT SET, STORE OBJECTIVES NAME "
                            "STARTING WITH e.g. 100X or 100x."
                        )

            # get and set image pixel sixe (x,y) for the current pixel size Config
            if self.magnification is not None:
                self.image_pixel_size = (
                    self.px_size_doubleSpinBox.value() / self.magnification
                )
                # print(f'IMAGE PIXEL SIZE xy = {self.image_pixel_size}')
                mmcore.setPixelSizeUm(
                    mmcore.getCurrentPixelSizeConfig(), self.image_pixel_size
                )
                print(f"Current Pixel Size in µm: {mmcore.getPixelSizeUm()}")

    def update_viewer(self, data):
        try:
            self.viewer.layers["preview"].data = data
        except KeyError:
            self.viewer.add_image(data, name="preview")

    def snap(self):
        self.stop_live()
        mmcore.setExposure(int(self.exp_spinBox.value()))
        # mmcore.setProperty("Cam", "Binning", self.bin_comboBox.currentText())
        # mmcore.setProperty("Cam", "PixelType", self.bit_comboBox.currentText())
        mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
        # mmcore.waitForDevice('')
        mmcore.snapImage()
        self.update_viewer(mmcore.getImage())

        # binning = mmcore.getProperty(mmcore.getCameraDevice(), "Binning")
        # print(f'Binning: {binning}')
        # bit = mmcore.getProperty(mmcore.getCameraDevice(), "PixelType")
        # print(f'Bit Depth: {bit}')

        try:  # display max and min gray values
            min_v = np.min(self.viewer.layers["preview"].data)
            self.min_val_lineEdit.setText(str(min_v))
            max_v = np.max(self.viewer.layers["preview"].data)
            self.max_val_lineEdit.setText(str(max_v))
        except KeyError:
            pass

    def start_live(self):
        from napari.qt import thread_worker

        @thread_worker(connect={"yielded": self.update_viewer})
        def live_mode():
            import time

            while True:
                mmcore.setExposure(int(self.exp_spinBox.value()))
                mmcore.setProperty("Cam", "Binning", self.bin_comboBox.currentText())
                mmcore.setProperty("Cam", "PixelType", self.bit_comboBox.currentText())
                mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
                mmcore.snapImage()
                yield mmcore.getImage()

                try:
                    min_v = np.min(self.viewer.layers["preview"].data)
                    self.min_val_lineEdit.setText(str(min_v))
                    max_v = np.max(self.viewer.layers["preview"].data)
                    self.max_val_lineEdit.setText(str(max_v))
                except KeyError:
                    pass

                time.sleep(0.03)

        self.live_Button.setText("Stop")
        self.worker = live_mode()

    def stop_live(self):
        if self.worker:
            self.worker.quit()
            self.worker = None
            self.live_Button.setText("Live")
            self.live_Button.setIcon(QIcon(str(icon_path / "vcam.svg")))
            self.live_Button.setIconSize(QtCore.QSize(40, 40))

    def toggle_live(self, event=None):
        # same as writing:
        # self.stop_live() if self.worker is not None else self.start_live()
        if self.worker is None:
            self.start_live()
            self.live_Button.setIcon(QIcon(str(icon_path / "cam_stop.svg")))
            self.live_Button.setIconSize(QtCore.QSize(40, 40))
        else:
            self.stop_live()
            self.live_Button.setIcon(QIcon(str(icon_path / "vcam.svg")))
        self.live_Button.setIconSize(QtCore.QSize(40, 40))
