from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt


class MMCameraWidget(QtW.QWidget):
    """
    Contains the following objects:

    px_size_doubleSpinBox: QtW.QDoubleSpinBox
    cam_roi_comboBox: QtW.QComboBox
    crop_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setHorizontalSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # cam_px widget and layout
        self.cam_px_wdg = QtW.QWidget()
        self.cam_px_layout = QtW.QGridLayout()
        # self.cam_px_layout.setSpacing(0)
        self.cam_px_layout.setVerticalSpacing(0)
        self.cam_px_layout.setHorizontalSpacing(5)
        # self.cam_px_layout.setContentsMargins(5, 9, 5, 5)
        self.cam_px_layout.setContentsMargins(0, 0, 0, 0)
        # label px in groupbox r0 c2
        self.cam_px_label = QtW.QLabel(text="Camera Pixel (µm):")
        self.cam_px_label.setMaximumWidth(120)
        self.cam_px_label.setMinimumWidth(120)
        self.cam_px_layout.addWidget(self.cam_px_label, 0, 0)
        # doublespinbox px in groupbox r0 c3
        self.px_size_doubleSpinBox = QtW.QDoubleSpinBox()
        self.px_size_doubleSpinBox.setMaximumWidth(100)
        self.px_size_doubleSpinBox.setMinimumWidth(60)
        self.px_size_doubleSpinBox.setMinimum(1.0)
        self.px_size_doubleSpinBox.setMinimumWidth(70)
        self.px_size_doubleSpinBox.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.cam_px_layout.addWidget(self.px_size_doubleSpinBox, 0, 1)

        self.cam_px_wdg.setLayout(self.cam_px_layout)

        self.main_layout.addWidget(self.cam_px_wdg, 0, 1)

        # camera roi widget and layout
        self.cam_roi_wdg = QtW.QWidget()
        self.cam_roi_wdg_layout = QtW.QGridLayout()
        self.cam_roi_wdg_layout.setHorizontalSpacing(5)
        self.cam_roi_wdg_layout.setContentsMargins(0, 0, 0, 0)

        # camera roi label in cam_roi_wdg
        self.cam_roi_label = QtW.QLabel(text="Camera ROI:")
        self.cam_roi_label.setMaximumWidth(80)
        self.cam_roi_label.setMinimumWidth(80)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_label, 0, 0)
        # combobox in cam_roi_wdg
        self.cam_roi_comboBox = QtW.QComboBox()
        self.cam_roi_comboBox.setEditable(True)
        self.cam_roi_comboBox.setMinimumWidth(70)
        self.cam_roi_wdg_layout.addWidget(self.cam_roi_comboBox, 0, 1)
        # pushbutton in cam_roi_wdg
        self.crop_Button = QtW.QPushButton(text="Crop")
        self.crop_Button.setMaximumWidth(60)
        self.cam_roi_wdg_layout.addWidget(self.crop_Button, 0, 2)
        # set cam_roi_wdg layout
        self.cam_roi_wdg.setLayout(self.cam_roi_wdg_layout)
        # cam_roi widget in groupbox
        self.main_layout.addWidget(self.cam_roi_wdg, 0, 0)

        # set layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMCameraWidget()
    win.show()
    sys.exit(app.exec_())
