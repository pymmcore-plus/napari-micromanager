#from qtpy import QtWidgets as QtW
from PyQt5 import QtWidgets as QtW

from qtpy import uic

from pathlib import Path
import pymmcore

UI_FILE = str(Path(__file__).parent / "micromanager_gui.ui")


class MainWindow(QtW.QMainWindow):
    
    # The UI_FILE above contains these objects:
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cgf_Button: QtW.QPushButton

    objective_comboBox: QtW.QComboBox
    
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox

    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit

    channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton







    def __init__(self, viewer):
        super().__init__()

        self.viewer = viewer

        uic.loadUi(UI_FILE, self)








#if __name__ == "__main__":
#    import sys

#    app = QtW.QApplication(sys.argv)
#    win = MainWindow()
#    win.show()
#    app.exec_()
