from qtpy import QtWidgets as QtW


class MMIlluminationWidget(QtW.QWidget):
    """
    Contains the following objects:

    illumination_Button: QtW.QLineEdit
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # pushbutton
        self.illumination_Button = QtW.QPushButton(text="Light Sources Control")
        self.illumination_Button.setMaximumSize(150, 25)

        self.main_layout.addWidget(self.illumination_Button)
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMIlluminationWidget()
    win.show()
    sys.exit(app.exec_())
