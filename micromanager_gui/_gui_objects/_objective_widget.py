from qtpy import QtWidgets as QtW


class MMObjectivesWidget(QtW.QWidget):
    """
    Contains the following objects:

    objective_groupBox: QtW.QGroupBox
    objective_comboBox: QtW.QLineEdit
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()

        # groupbox in widget
        self.objective_groupBox = QtW.QGroupBox()
        self.objective_groupBox.setTitle("Objectives")
        self.main_layout.addWidget(self.objective_groupBox, 0, 0)
        self.setLayout(self.main_layout)

        # combobox in groupbox
        self.objective_groupBox_layout = QtW.QGridLayout()
        self.objective_groupBox_layout.setSpacing(0)
        self.objective_groupBox_layout.setContentsMargins(9, 9, 9, 9)
        self.objective_comboBox = QtW.QComboBox()
        self.objective_comboBox.setMinimumSize(160, 0)
        self.objective_groupBox_layout.addWidget(self.objective_comboBox, 0, 0)
        self.objective_groupBox.setLayout(self.objective_groupBox_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMObjectivesWidget()
    win.show()
    sys.exit(app.exec_())
