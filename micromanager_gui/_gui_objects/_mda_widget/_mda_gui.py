from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class MMMDAWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(10, 10, 10, 10)

        # general scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.explorer_wdg = self._create_gui()
        self._scroll.setWidget(self.explorer_wdg)
        self.layout().addWidget(self._scroll)

    def _create_gui(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(20)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)

        self.save_groupBox = self._create_save_group()
        wdg_layout.addWidget(self.save_groupBox)

        self.channel_groupBox = self._create_channel_group()
        wdg_layout.addWidget(self.channel_groupBox)

        self.time_groupBox = self._create_time_group()
        wdg_layout.addWidget(self.time_groupBox)

        self.stack_groupBox = self._create_stack_groupBox()
        wdg_layout.addWidget(self.stack_groupBox)

        self.stage_pos_groupBox = self._create_stage_pos_groupBox()
        wdg_layout.addWidget(self.stage_pos_groupBox)

        # spacer = QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        # wdg_layout.addItem(spacer)

        return wdg

    def _create_save_group(self):
        group = QGroupBox(title="Save MDA")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group.setCheckable(True)
        group.setChecked(False)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(0)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # directory
        dir_group = QWidget()
        dir_group_layout = QHBoxLayout()
        dir_group_layout.setSpacing(5)
        dir_group_layout.setContentsMargins(10, 10, 10, 10)
        dir_group.setLayout(dir_group_layout)
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_lbl_size = 70
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        dir_lbl = QLabel(text="Directory:")
        dir_lbl.setMinimumWidth(min_lbl_size)
        dir_lbl.setSizePolicy(lbl_sizepolicy)
        self.dir_lineEdit = QLineEdit()
        self.browse_save_Button = QPushButton(text="...")
        self.browse_save_Button.setSizePolicy(btn_sizepolicy)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_lineEdit)
        dir_group_layout.addWidget(self.browse_save_Button)

        # filename
        fname_group = QWidget()
        fname_group_layout = QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(10, 10, 10, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_lineEdit = QLineEdit()
        self.fname_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_lineEdit)

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)

        # checkbox
        self.checkBox_save_pos = QCheckBox(
            text="Save XY Positions in separate files (ImageJ compatibility)"
        )
        group_layout.addWidget(self.checkBox_save_pos)

        return group

    def _create_channel_group(self):

        group = QGroupBox(title="Channels")
        group.setMinimumHeight(230)
        group_layout = QGridLayout()
        group_layout.setHorizontalSpacing(15)
        group_layout.setVerticalSpacing(0)
        group_layout.setContentsMargins(10, 0, 10, 0)
        group.setLayout(group_layout)

        # table
        self.channel_explorer_tableWidget = QTableWidget()
        self.channel_explorer_tableWidget.setMinimumHeight(90)
        hdr = self.channel_explorer_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.channel_explorer_tableWidget.verticalHeader().setVisible(False)
        self.channel_explorer_tableWidget.setTabKeyNavigation(True)
        self.channel_explorer_tableWidget.setColumnCount(2)
        self.channel_explorer_tableWidget.setRowCount(0)
        self.channel_explorer_tableWidget.setHorizontalHeaderLabels(
            ["Channel", "Exposure Time (ms)"]
        )
        group_layout.addWidget(self.channel_explorer_tableWidget, 0, 0, 3, 1)

        # buttons
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_size = 100
        self.add_ch_explorer_Button = QPushButton(text="Add")
        self.add_ch_explorer_Button.setMinimumWidth(min_size)
        self.add_ch_explorer_Button.setSizePolicy(btn_sizepolicy)
        self.remove_ch_explorer_Button = QPushButton(text="Remove")
        self.remove_ch_explorer_Button.setMinimumWidth(min_size)
        self.remove_ch_explorer_Button.setSizePolicy(btn_sizepolicy)
        self.clear_ch_explorer_Button = QPushButton(text="Clear")
        self.clear_ch_explorer_Button.setMinimumWidth(min_size)
        self.clear_ch_explorer_Button.setSizePolicy(btn_sizepolicy)

        group_layout.addWidget(self.add_ch_explorer_Button, 0, 1, 1, 1)
        group_layout.addWidget(self.remove_ch_explorer_Button, 1, 1, 1, 2)
        group_layout.addWidget(self.clear_ch_explorer_Button, 2, 1, 1, 2)

        return group

    def _create_time_group(self):
        pass

    def _create_stack_groupBox(self):
        pass

    def _create_stage_pos_groupBox(self):
        pass


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = MMMDAWidget()
    win.show()
    sys.exit(app.exec_())
