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

        # main_layout
        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # cam_roi_wdg and layout
        self.cam_roi_wdg = QtW.QWidget()
        self.cam_roi_wdg_layout = QtW.QHBoxLayout()
        self.cam_roi_wdg_layout.setSpacing(5)
        self.cam_roi_wdg_layout.setContentsMargins(0, 0, 0, 0)
        # cam_roi_label
        self.cam_roi_label = QtW.QLabel(text="Camera ROI:")
        self.cam_roi_label.setMaximumWidth(80)
        self.cam_roi_label.setMinimumWidth(80)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_label)
        # cam_roi_comboBox
        self.cam_roi_comboBox = QtW.QComboBox()
        self.cam_roi_comboBox.setMinimumWidth(70)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_comboBox)
        # crop_Button
        self.crop_Button = QtW.QPushButton(text="Crop")
        self.crop_Button.setMaximumWidth(60)
        self.cam_roi_wdg_layout.addWidget(self.crop_Button)
        # set cam_roi_wdg layout add to main_layout
        self.cam_roi_wdg.setLayout(self.cam_roi_wdg_layout)
        self.main_layout.addWidget(self.cam_roi_wdg)

        # cam_px_wdg and layout
        self.cam_px_wdg = QtW.QWidget()
        self.cam_px_layout = QtW.QHBoxLayout()
        self.cam_px_layout.setContentsMargins(0, 0, 0, 0)
        self.cam_px_layout.setSpacing(5)
        self.cam_px_layout.setContentsMargins(0, 0, 0, 0)
        # cam_px_label
        self.cam_px_label = QtW.QLabel(text="Camera Pixel (µm):")
        self.cam_px_label.setMaximumWidth(120)
        self.cam_px_label.setMinimumWidth(120)
        self.cam_px_layout.addWidget(self.cam_px_label)
        # px_size_doubleSpinBox
        self.px_size_doubleSpinBox = QtW.QDoubleSpinBox()
        self.px_size_doubleSpinBox.setMaximumWidth(120)
        self.px_size_doubleSpinBox.setMinimumWidth(60)
        self.px_size_doubleSpinBox.setMinimum(1.0)
        self.px_size_doubleSpinBox.setMinimumWidth(70)
        self.px_size_doubleSpinBox.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.cam_px_layout.addWidget(self.px_size_doubleSpinBox)
        # set cam_px_wdg layout add to main_layout
        self.cam_px_wdg.setLayout(self.cam_px_layout)
        self.main_layout.addWidget(self.cam_px_wdg)

        # set main layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMCameraWidget()
    win.show()
    sys.exit(app.exec_())
