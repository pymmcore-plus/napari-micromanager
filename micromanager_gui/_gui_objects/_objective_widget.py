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

        # main_layout
        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # obj_label
        self.obj_label = QtW.QLabel(text="Objectives:")
        self.obj_label.setMinimumWidth(80)
        self.obj_label.setMaximumWidth(80)
        self.main_layout.addWidget(self.obj_label)

        # objective_comboBox
        self.objective_comboBox = QtW.QComboBox()
        self.objective_comboBox.setMinimumWidth(285)
        self.main_layout.addWidget(self.objective_comboBox)

        # Set main layout
        self.setLayout(self.main_layout)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMObjectivesWidget()
    win.show()
    sys.exit(app.exec_())
