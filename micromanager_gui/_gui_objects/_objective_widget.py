from qtpy import QtWidgets as QtW


class MMObjectivesWidget(QtW.QWidget):
    """
    Contains the following objects:

    objective_comboBox: QtW.QComboBox
    """

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 15, 0)

        # label
        self.obj_label = QtW.QLabel(text="Objectives:")
        self.obj_label.setMaximumWidth(80)
        self.main_layout.addWidget(self.obj_label, 0, 0)

        # combobox
        self.objective_comboBox = QtW.QComboBox()
        self.objective_comboBox.setMinimumWidth(250)
        self.main_layout.addWidget(self.objective_comboBox, 0, 1)

        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMObjectivesWidget()
    win.show()
    sys.exit(app.exec_())
