from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

from .explore_sample import ExploreSample
from .multid_widget import MultiDWidget
from .qmmcore import QMMCore

if TYPE_CHECKING:
    import napari

ICONS = Path(__file__).parent / "icons"
UI_FILE = str(Path(__file__).parent / "_ui" / "micromanager_gui.ui")

mmcore = QMMCore()


class MainWindow(QtW.QMainWindow):

    # The UI_FILE above contains these objects:
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cfg_Button: QtW.QPushButton
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

        self.cfg_LineEdit.setText("demo")

        mmcore.system_configuration_loaded.connect(self._on_system_configuration_loaded)
        mmcore.xy_stage_position_changed.connect(self._on_xy_stage_position_changed)
        mmcore.stage_position_changed.connect(self._on_stage_position_changed)
        mmcore.stack_to_viewer.connect(self.add_stack_mda)

        # create MultiDWidget() widgets
        self.mda = MultiDWidget()

        self.explorer = ExploreSample()
        self.explorer.new_frame.connect(self.add_frame_explorer)
        self.explorer.delete_snaps.connect(self.delete_layer)
        self.explorer.delete_previous_scan.connect(self.delete_layer)

        # create tab widgets
        multid_tab = QtW.QWidget(self)
        multid_tab.layout = QtW.QGridLayout()
        multid_tab.layout.addWidget(self.mda)
        multid_tab.setLayout(multid_tab.layout)

        explorer_tab = QtW.QWidget(self)
        explorer_tab.layout = QtW.QGridLayout()
        explorer_tab.layout.addWidget(self.explorer)
        explorer_tab.setLayout(explorer_tab.layout)

        # create tabs layout and add the widgets
        self.tabWidget.addTab(multid_tab, "Multi-D Acquisition")
        self.tabWidget.addTab(explorer_tab, "Sample Explorer")

        # connect buttons
        self.load_cfg_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)

        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)

        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        # stage button icons
        self.left_Button.setIcon(QIcon(str(ICONS / "left_arrow_1_green.svg")))
        self.left_Button.setIconSize(QSize(30, 30))
        self.right_Button.setIcon(QIcon(str(ICONS / "right_arrow_1_green.svg")))
        self.right_Button.setIconSize(QSize(30, 30))
        self.y_up_Button.setIcon(QIcon(str(ICONS / "up_arrow_1_green.svg")))
        self.y_up_Button.setIconSize(QSize(30, 30))
        self.y_down_Button.setIcon(QIcon(str(ICONS / "down_arrow_1_green.svg")))
        self.y_down_Button.setIconSize(QSize(30, 30))
        self.up_Button.setIcon(QIcon(str(ICONS / "up_arrow_1_green.svg")))
        self.up_Button.setIconSize(QSize(30, 30))
        self.down_Button.setIcon(QIcon(str(ICONS / "down_arrow_1_green.svg")))
        self.down_Button.setIconSize(QSize(30, 30))
        # snap/live icons
        self.snap_Button.setIcon(QIcon(str(ICONS / "cam.svg")))
        self.snap_Button.setIconSize(QSize(30, 30))
        self.live_Button.setIcon(QIcon(str(ICONS / "vcam.svg")))
        self.live_Button.setIconSize(QSize(40, 40))

        # connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)

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

    # TO DO: add the file name form the save box
    def add_stack_mda(self, stack, cnt, xy_pos):
        name = f"Exp{cnt}_Pos{xy_pos}"
        try:
            layer = self.viewer.layers[name]
            layer.data = stack
        except KeyError:
            self.viewer.add_image(stack, name=name)

    def browse_cfg(self):
        mmcore.unloadAllDevices()  # unload all devicies
        print(f"Loaded Devicies: {mmcore.getLoadedDevices()}")

        # clear spinbox/combobox
        self.objective_comboBox.clear()
        self.bin_comboBox.clear()
        self.bit_comboBox.clear()
        self.snap_channel_comboBox.clear()

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "⁩", "cfg(*.cfg)")
        self.cfg_LineEdit.setText(str(file_dir[0]))
        # self.setEnabled(False)
        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")
        self.load_cfg_Button.setEnabled(True)

    def load_cfg(self):
        self.load_cfg_Button.setEnabled(False)
        mmcore.loadSystemConfiguration(self.cfg_LineEdit.text())

    def _refresh_camera_options(self):
        cam_device = mmcore.getCameraDevice()
        cam_props = mmcore.getDevicePropertyNames(cam_device)
        if "Binning" in cam_props:
            bin_opts = mmcore.getAllowedPropertyValues(cam_device, "Binning")
            self.bin_comboBox.addItems(bin_opts)
            self.bin_comboBox.setCurrentText(mmcore.getProperty(cam_device, "Binning"))

        if "PixelType" in cam_props:
            px_t = mmcore.getAllowedPropertyValues(cam_device, "PixelType")
            self.bit_comboBox.addItems(px_t)
            if "16" in px_t:
                self.bit_comboBox.setCurrentText("16bit")
                mmcore.setProperty(cam_device, "PixelType", "16bit")

    def _refresh_objective_options(self):
        if "Objective" in mmcore.getLoadedDevices():
            self.objective_comboBox.addItems(mmcore.getStateLabels("Objective"))

    def _refresh_channel_list(self):
        if "Channel" in mmcore.getAvailableConfigGroups():
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.snap_channel_comboBox.addItems(channel_list)
            self.explorer.scan_channel_comboBox.addItems(channel_list)

    def _on_system_configuration_loaded(self):
        self._refresh_camera_options()
        self._refresh_objective_options()
        self._refresh_channel_list()
        x, y = mmcore.getXPosition(), mmcore.getYPosition()
        self._on_xy_stage_position_changed(mmcore.getXYStageDevice(), x, y)

    def bit_changed(self):
        if self.bit_comboBox.count() > 0:
            bits = self.bit_comboBox.currentText()
            mmcore.setProperty(mmcore.getCameraDevice(), "PixelType", bits)
            pixel_type = mmcore.getProperty(mmcore.getCameraDevice(), "PixelType")
            print(f"PixelType: {pixel_type}")

    def bin_changed(self):
        if self.bin_comboBox.count() > 0:
            bins = self.bin_comboBox.currentText()
            mmcore.setProperty(mmcore.getCameraDevice(), "Binning", bins)
            print(f'Binning: {mmcore.getProperty(mmcore.getCameraDevice(), "Binning")}')

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if name == mmcore.getFocusDevice():
            self.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        mmcore.setRelPosition(dx=-float(self.xy_step_size_SpinBox.value()))

    def stage_x_right(self):
        mmcore.setRelPosition(dx=float(self.xy_step_size_SpinBox.value()))

    def stage_y_up(self):
        mmcore.setRelPosition(dy=float(self.xy_step_size_SpinBox.value()))

    def stage_y_down(self):
        mmcore.setRelPosition(dy=-float(self.xy_step_size_SpinBox.value()))

    def stage_z_up(self):
        mmcore.setRelPosition(dz=float(self.z_step_size_doubleSpinBox.value()))

    def stage_z_down(self):
        mmcore.setRelPosition(dz=-float(self.z_step_size_doubleSpinBox.value()))

    def change_objective(self):
        if not self.objective_comboBox.count() > 0:
            return

        zdev = mmcore.getFocusDevice()

        print("\nchanging objective...")
        currentZ = mmcore.getZPosition()
        print(f"currentZ: {currentZ}")
        mmcore.setPosition(zdev, 0)
        mmcore.waitForDevice(zdev)
        print(self.objective_comboBox.currentText())
        mmcore.setProperty("Objective", "Label", self.objective_comboBox.currentText())
        mmcore.waitForDevice("Objective")
        print(f"downpos: {mmcore.getZPosition()}")
        mmcore.setPosition(zdev, currentZ)
        mmcore.waitForDevice(zdev)
        print(f"upagain: {mmcore.getZPosition()}")
        print(f"OBJECTIVE: {mmcore.getProperty('Objective', 'Label')}")

        # define and set pixel size Config
        mmcore.deletePixelSizeConfig(mmcore.getCurrentPixelSizeConfig())
        curr_obj_name = mmcore.getProperty("Objective", "Label")
        mmcore.definePixelSizeConfig(curr_obj_name)
        mmcore.setPixelSizeConfig(curr_obj_name)
        print(f"Current pixel cfg: {mmcore.getCurrentPixelSizeConfig()}")

        magnification = None
        # get magnification info from the objective
        for i in range(len(curr_obj_name)):
            character = curr_obj_name[i]
            if character == "X" or character == "x":
                if i <= 3:
                    magnification_string = curr_obj_name[:i]
                    magnification = int(magnification_string)
                    print(f"Current Magnification: {magnification}X")
                else:
                    print(
                        "MAGNIFICATION NOT SET, STORE OBJECTIVES NAME "
                        "STARTING WITH e.g. 100X or 100x."
                    )

        # get and set image pixel sixe (x,y) for the current pixel size Config
        if magnification is not None:
            self.image_pixel_size = self.px_size_doubleSpinBox.value() / magnification
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
        mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
        # mmcore.waitForDevice('')
        mmcore.snapImage()
        self.update_viewer(mmcore.getImage())

    def start_live(self):
        from napari.qt import thread_worker

        @thread_worker(connect={"yielded": self.update_viewer})
        def live_mode():
            import time

            camdev = mmcore.getCameraDevice()

            while True:
                mmcore.setExposure(int(self.exp_spinBox.value()))
                mmcore.setProperty(camdev, "Binning", self.bin_comboBox.currentText())
                mmcore.setProperty(camdev, "PixelType", self.bit_comboBox.currentText())
                mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
                mmcore.snapImage()
                yield mmcore.getImage()
                time.sleep(0.02)

        self.live_Button.setText("Stop")
        self.worker = live_mode()

    def stop_live(self):
        if self.worker:
            self.worker.quit()
            self.worker = None
            self.live_Button.setText("Live")
            self.live_Button.setIcon(QIcon(str(ICONS / "vcam.svg")))
            self.live_Button.setIconSize(QSize(40, 40))

    def toggle_live(self, event=None):
        # same as writing:
        # self.stop_live() if self.worker is not None else self.start_live()
        if self.worker is None:
            self.start_live()
            self.live_Button.setIcon(QIcon(str(ICONS / "cam_stop.svg")))
            self.live_Button.setIconSize(QSize(40, 40))
        else:
            self.stop_live()
            self.live_Button.setIcon(QIcon(str(ICONS / "vcam.svg")))
        self.live_Button.setIconSize(QSize(40, 40))
