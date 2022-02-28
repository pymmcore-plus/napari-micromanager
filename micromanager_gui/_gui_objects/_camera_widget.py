from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt


class MMCameraWidget(QtW.QWidget):
    """
    Contains the following objects:

    camera_groupBox: QtW.QGroupBox
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox
    px_size_doubleSpinBox: QtW.QDoubleSpinBox
    cam_roi_comboBox: QtW.QComboBox
    crop_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # camera groupbox in widget
        self.camera_groupBox = QtW.QGroupBox()
        self.camera_groupBox.setTitle("Camera")
        self.camera_groupBox.setMaximumHeight(135)
        self.main_layout.addWidget(self.camera_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # define camera_groupBox layout
        self.camera_groupBox_layout = QtW.QGridLayout()
        # self.camera_groupBox_layout.setSpacing(0)
        self.camera_groupBox_layout.setHorizontalSpacing(3)
        self.camera_groupBox_layout.setVerticalSpacing(0)
        self.camera_groupBox_layout.setContentsMargins(5, 5, 5, 0)
        # add to camera_groupBox layout:
        # bin widget and layout
        self.bin_wdg = QtW.QWidget()
        self.bin_layout = QtW.QGridLayout()
        self.bin_layout.setSpacing(0)
        self.bin_layout.setContentsMargins(0, 0, 3, 0)
        # label bin in layout
        self.bin_label = QtW.QLabel(text="Binning:  ")
        self.bin_label.setMaximumWidth(65)
        self.bin_layout.addWidget(self.bin_label, 0, 0)
        # combobox bin in layout
        self.bin_comboBox = QtW.QComboBox()
        self.bin_layout.addWidget(self.bin_comboBox, 0, 1)
        # set bin_wdg layout
        self.bin_wdg.setLayout(self.bin_layout)
        # bin widget in groupbox
        self.camera_groupBox_layout.addWidget(self.bin_wdg, 0, 0)

        # bit widget and layout
        self.bit_wdg = QtW.QWidget()
        self.bit_layout = QtW.QGridLayout()
        self.bin_layout.setSpacing(0)
        self.bit_layout.setContentsMargins(0, 0, 3, 0)
        # label bit in groupbox r1 c0
        self.bit_label = QtW.QLabel(text="Bit Depth:")
        self.bit_label.setMaximumWidth(65)
        self.bit_layout.addWidget(self.bit_label, 0, 0)
        # combobox bit in groupbox r1 c1
        self.bit_comboBox = QtW.QComboBox()
        self.bit_layout.addWidget(self.bit_comboBox, 0, 1)
        # set bit_wdg layout
        self.bit_wdg.setLayout(self.bit_layout)
        # bit widget in groupbox
        self.camera_groupBox_layout.addWidget(self.bit_wdg, 1, 0)

        # cam_px widget and layout
        self.cam_px_wdg = QtW.QWidget()
        self.cam_px_layout = QtW.QGridLayout()
        # self.cam_px_layout.setSpacing(0)
        self.cam_px_layout.setVerticalSpacing(0)
        self.cam_px_layout.setHorizontalSpacing(2)
        self.cam_px_layout.setContentsMargins(0, 0, 0, 0)
        # label px in groupbox r0 c2
        self.cam_px_label = QtW.QLabel(text="Pixel (µm):")
        self.cam_px_label.setMaximumWidth(70)
        self.cam_px_layout.addWidget(self.cam_px_label, 0, 0)
        # doublespinbox px in groupbox r0 c3
        self.px_size_doubleSpinBox = QtW.QDoubleSpinBox()
        self.px_size_doubleSpinBox.setMinimum(1.0)
        self.px_size_doubleSpinBox.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.cam_px_layout.addWidget(self.px_size_doubleSpinBox, 0, 1)
        # set bit_wdg layout
        self.cam_px_wdg.setLayout(self.cam_px_layout)
        # bit widget in groupbox
        self.camera_groupBox_layout.addWidget(self.cam_px_wdg, 0, 1)

        # camera roi widget and layout
        self.cam_roi_wdg = QtW.QWidget()
        self.cam_roi_wdg_layout = QtW.QGridLayout()
        self.cam_roi_wdg_layout.setContentsMargins(0, 0, 0, 0)
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
        self.crop_Button.setMaximumWidth(60)
        self.cam_roi_wdg_layout.addWidget(self.crop_Button, 0, 2)
        # set cam_roi_wdg layout
        self.cam_roi_wdg.setLayout(self.cam_roi_wdg_layout)
        # cam_roi widget in groupbox
        self.camera_groupBox_layout.addWidget(self.cam_roi_wdg, 1, 1)

        # set layout camera_groupBox
        self.camera_groupBox.setLayout(self.camera_groupBox_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMCameraWidget()
    win.show()
    sys.exit(app.exec_())
