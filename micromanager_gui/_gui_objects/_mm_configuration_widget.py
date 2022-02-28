from qtpy import QtWidgets as QtW


class MMConfigurationWidget(QtW.QWidget):
    """
    Contains the following objects:
    cfg_groupBox: QtW.QGroupBox
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cfg_Button: QtW.QPushButton
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        # main_layout
        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # cfg_groupBox and layout
        self.cfg_groupBox = QtW.QGroupBox()
        self.cfg_groupBox.setTitle("Micro-Manager Configuration")
        self.cfg_groupBox_layout = QtW.QHBoxLayout()
        self.cfg_groupBox_layout.setContentsMargins(5, 9, 5, 3)

        # cfg_LineEdit
        self.cfg_LineEdit = QtW.QLineEdit()
        self.cfg_LineEdit.setPlaceholderText("MMConfig_demo.cfg")

        # browse_cfg_Button
        self.browse_cfg_Button = QtW.QPushButton(text="...")

        # load_cfg_Button
        self.load_cfg_Button = QtW.QPushButton(text="Load")
        self.load_cfg_Button.setMinimumWidth(60)

        # add widgets
        self.cfg_groupBox_layout.addWidget(self.cfg_LineEdit)
        self.cfg_groupBox_layout.addWidget(self.browse_cfg_Button)
        self.cfg_groupBox_layout.addWidget(self.load_cfg_Button)
        self.cfg_groupBox.setLayout(self.cfg_groupBox_layout)
        self.main_layout.addWidget(self.cfg_groupBox)

        # Set main layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMConfigurationWidget()
    win.show()
    sys.exit(app.exec_())
