from qtpy import QtWidgets as QtW


class MMPropertyBrowserWidget(QtW.QWidget):
    """
    Contains the following objects:

    properties_groupBox: QtW.QGroupBox
    properties_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        # groupbox in widget
        self.properties_groupBox = QtW.QGroupBox()
        # self.properties_groupBox.
        self.properties_groupBox.setMaximumWidth(140)
        self.properties_groupBox.setTitle("Property Browser")
        self.main_layout.addWidget(self.properties_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # PushButton in groupbox
        self.properties_groupBox_layout = QtW.QGridLayout()
        self.properties_groupBox_layout.setSpacing(0)
        self.properties_groupBox_layout.setContentsMargins(9, 9, 9, 9)
        self.properties_Button = QtW.QPushButton(text="Properties")
        self.properties_Button.setMaximumSize(110, 50)

        self.properties_groupBox_layout.addWidget(self.properties_Button, 0, 0)
        self.properties_groupBox.setLayout(self.properties_groupBox_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMPropertyBrowserWidget()
    win.show()
    sys.exit(app.exec_())
