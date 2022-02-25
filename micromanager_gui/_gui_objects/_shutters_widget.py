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

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setVerticalSpacing(0)
        self.main_layout.setHorizontalSpacing(8)
        self.main_layout.setContentsMargins(0, 0, 15, 0)

        # label
        self.shutter_label = QtW.QLabel(text="Shutters:")
        self.shutter_label.setMaximumWidth(80)
        self.main_layout.addWidget(self.shutter_label, 0, 0)

        # combobox
        self.shutter_comboBox = QtW.QComboBox()
        self.shutter_comboBox.setMinimumWidth(200)
        self.main_layout.addWidget(self.shutter_comboBox, 0, 1)

        # pushbutton
        self.shutter_btn = QtW.QPushButton(text="Open")
        self.shutter_btn.setMinimumWidth(80)
        self.shutter_btn.setMaximumWidth(80)
        self.main_layout.addWidget(self.shutter_btn, 0, 2)

        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMShuttersWidget()
    win.show()
    sys.exit(app.exec_())
