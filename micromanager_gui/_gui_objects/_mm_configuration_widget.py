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

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # cfg groupbox in widget
        self.cfg_groupBox = QtW.QGroupBox()
        # self.cfg_groupBox.setMinimumHeight(65)
        self.cfg_groupBox.setTitle("Micro-Manager Configuration")
        self.main_layout.addWidget(self.cfg_groupBox, 0, 0)

        # define camera_groupBox layout
        self.cfg_groupBox_layout = QtW.QGridLayout()
        self.cfg_groupBox_layout.setContentsMargins(5, 7, 5, 3)

        # add to cfg_groupBox layout:
        self.cfg_LineEdit = QtW.QLineEdit()
        self.cfg_LineEdit.setPlaceholderText("MMConfig_demo.cfg")
        self.browse_cfg_Button = QtW.QPushButton(text="...")
        self.load_cfg_Button = QtW.QPushButton(text="Load")
        self.load_cfg_Button.setMinimumWidth(60)
        # widgets in in cfg_groupBox layout
        self.cfg_groupBox_layout.addWidget(self.cfg_LineEdit, 0, 0)
        self.cfg_groupBox_layout.addWidget(self.browse_cfg_Button, 0, 1)
        self.cfg_groupBox_layout.addWidget(self.load_cfg_Button, 0, 2)
        # set cfg_groupBox layout
        self.cfg_groupBox.setLayout(self.cfg_groupBox_layout)

        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMConfigurationWidget()
    win.show()
    sys.exit(app.exec_())
