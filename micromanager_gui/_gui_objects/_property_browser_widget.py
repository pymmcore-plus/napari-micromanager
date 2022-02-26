from qtpy import QtWidgets as QtW


class MMPropertyBrowserWidget(QtW.QWidget):
    """
    Contains the following objects:

    properties_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # pushbutton
        self.properties_Button = QtW.QPushButton(text="Property Browser")
        self.properties_Button.setMaximumSize(135, 25)
        self.main_layout.addWidget(self.properties_Button)

        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMPropertyBrowserWidget()
    win.show()
    sys.exit(app.exec_())
