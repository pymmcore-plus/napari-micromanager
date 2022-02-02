from pathlib import Path

from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

ICONS = Path(__file__).parent.parent / "icons"


class MMTabWidget(QtW.QWidget):

    MM_TAB = str(Path(__file__).parent / "mm_snap_and_tabs.ui")

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


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMTabWidget()
    win.show()
    sys.exit(app.exec_())
