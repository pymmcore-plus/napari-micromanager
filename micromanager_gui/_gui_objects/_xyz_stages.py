from pathlib import Path

from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

ICONS = Path(__file__).parent.parent / "icons"


class MMStagesWidget(QtW.QWidget):

    MM_XYZ_STAGE = str(Path(__file__).parent / "mm_xyz_stage.ui")

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


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMStagesWidget()
    win.show()
    sys.exit(app.exec_())
