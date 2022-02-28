from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from .._core_funcs import _update_pixel_size

policy_max = QtW.QSizePolicy.Policy.Maximum


class MMCameraWidget(QtW.QWidget):
    """A Widget to control camera ROI"""

    def __init__(self):
        super().__init__()

        self.cam_roi_comboBox = QtW.QComboBox()
        self.crop_Button = QtW.QPushButton("Crop")
        self.px_size_doubleSpinBox = QtW.QDoubleSpinBox()
        self.px_size_doubleSpinBox.setMinimum(1.0)
        self.px_size_doubleSpinBox.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

        cam_px_label = QtW.QLabel("Camera Pixel (µm):")
        cam_px_label.setSizePolicy(policy_max, policy_max)
        roi_label = QtW.QLabel("Camera ROI:")
        roi_label.setSizePolicy(policy_max, policy_max)

        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(roi_label)
        layout.addWidget(self.cam_roi_comboBox)
        layout.addWidget(self.crop_Button)
        layout.addWidget(cam_px_label)
        layout.addWidget(self.px_size_doubleSpinBox)
        self.setLayout(layout)

        self.px_size_doubleSpinBox.valueChanged.connect(_update_pixel_size)

    def setEnabled(self, enabled: bool) -> None:
        self.cam_roi_comboBox.setEnabled(enabled)
        self.crop_Button.setEnabled(enabled)
        self.px_size_doubleSpinBox.setEnabled(enabled)
