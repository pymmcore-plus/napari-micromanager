from qtpy import QtWidgets as QtW
from qtpy import uic

from pathlib import Path
import pymmcore

UI_FILE = str(Path(__file__).parent / "micromanager.ui")


class MainWindow(QtW.QMainWindow):
    
    # The UI_FILE above contains these objects:

    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_FILE, self)






if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec_()
