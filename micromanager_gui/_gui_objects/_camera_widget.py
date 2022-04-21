from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from .. import _core

policy_max = QtW.QSizePolicy.Policy.Maximum


class MMCameraWidget(QtW.QWidget):
    """A Widget to control camera ROI and pixel size."""

    def __init__(self):
        super().__init__()

        self.cam_roi_combo = QtW.QComboBox()
        self.crop_btn = QtW.QPushButton("Crop")
        self.px_size_spinbox = QtW.QDoubleSpinBox()
        center = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        self.px_size_spinbox.setAlignment(center)

        cam_px_label = QtW.QLabel("Camera Pixel (µm):")
        cam_px_label.setSizePolicy(policy_max, policy_max)
        roi_label = QtW.QLabel("Camera ROI:")
        roi_label.setSizePolicy(policy_max, policy_max)

        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(roi_label)
        layout.addWidget(self.cam_roi_combo)
        layout.addWidget(self.crop_btn)
        layout.addWidget(cam_px_label)
        layout.addWidget(self.px_size_spinbox)
        self.setLayout(layout)

        self.px_size_spinbox.valueChanged.connect(_core.update_pixel_size)

    def setEnabled(self, enabled: bool) -> None:
        self.cam_roi_combo.setEnabled(enabled)
        self.crop_btn.setEnabled(enabled)
        self.px_size_spinbox.setEnabled(enabled)

    def _update_pixel_size(self):
        """Update core pixel size config using the current pixel size spinbox."""
        _core.update_pixel_size(self.px_size_spinbox.value())
