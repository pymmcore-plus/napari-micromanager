from qtpy import QtWidgets as QtW


class MMShuttersWidget(QtW.QWidget):
    """
    Contains the following objects:

    shutter_comboBox: QtW.QComboBox
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        # main_layout
        self.main_layout = QtW.QGridLayout()
        self.main_layout.setHorizontalSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # shutter_label
        self.shutter_label = QtW.QLabel(text="Shutters:")
        self.shutter_label.setMaximumWidth(80)
        self.shutter_label.setMinimumWidth(80)
        self.main_layout.addWidget(self.shutter_label, 0, 0)

        # shutter_comboBox
        self.shutter_comboBox = QtW.QComboBox()
        self.shutter_comboBox.setMinimumWidth(200)
        self.main_layout.addWidget(self.shutter_comboBox, 0, 1)

        # shutter pushbutton
        self.shutter_btn = QtW.QPushButton(text="Open")
        self.shutter_btn.setMinimumWidth(80)
        self.shutter_btn.setMaximumWidth(80)
        self.main_layout.addWidget(self.shutter_btn, 0, 2)

        # Set main layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMShuttersWidget()
    win.show()
    sys.exit(app.exec_())
