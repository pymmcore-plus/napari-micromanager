from qtpy import QtCore
from qtpy import QtWidgets as QtW


class MMIlluminationWidget(QtW.QWidget):
    """
    contains the following objects:
    - illumination_groupBox: QtW.QGroupBox
    - illumination_Button: QtW.QLineEdit
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # groupbox in widget
        self.illumination_groupBox = QtW.QGroupBox()
        self.illumination_groupBox.setTitle("Illumination")
        self.main_layout.addWidget(self.illumination_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # PushButton in groupbox
        self.illumination_groupBox_layout = QtW.QGridLayout()
        self.illumination_Button = QtW.QPushButton(text="Illumination")
        self.illumination_groupBox.setMinimumSize(QtCore.QSize(160, 0))

        self.illumination_groupBox_layout.addWidget(self.illumination_Button, 0, 0)
        self.illumination_groupBox.setLayout(self.illumination_groupBox_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMIlluminationWidget()
    win.show()
    sys.exit(app.exec_())
