from typing import Optional

from fonticon_mdi6 import MDI6
from qtpy import QtCore
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon


class MMExplorerWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

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

        self.scan_props = self._create_row_cols_overlap_group()
        wdg_layout.addWidget(self.scan_props)

        self.channel_explorer_groupBox = self._create_channel_group()
        wdg_layout.addWidget(self.channel_explorer_groupBox)

        self.save_explorer_groupBox = self._create_save_group()
        wdg_layout.addWidget(self.save_explorer_groupBox)

        self.btns = self._create_start_stop_buttons()
        wdg_layout.addWidget(self.btns)

        self.move_to_pos = self._create_move_to_pos()
        wdg_layout.addWidget(self.move_to_pos)

        return wdg

    def _create_row_cols_overlap_group(self):
        group = QGroupBox(title="Scan Parameters")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QHBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # row
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.row_wdg = QWidget()
        row_wdg_lay = QHBoxLayout()
        row_wdg_lay.setSpacing(0)
        row_wdg_lay.setContentsMargins(0, 0, 0, 0)
        self.row_wdg.setLayout(row_wdg_lay)
        row_label = QLabel(text="Row:")
        row_label.setSizePolicy(lbl_sizepolicy)
        self.scan_size_spinBox_r = QSpinBox()
        self.scan_size_spinBox_r.setAlignment(Qt.AlignCenter)
        row_wdg_lay.addWidget(row_label)
        row_wdg_lay.addWidget(self.scan_size_spinBox_r)

        # col
        self.col_wdg = QWidget()
        col_wdg_lay = QHBoxLayout()
        col_wdg_lay.setSpacing(0)
        col_wdg_lay.setContentsMargins(0, 0, 0, 0)
        self.col_wdg.setLayout(col_wdg_lay)
        col_label = QLabel(text="Col:")
        col_label.setSizePolicy(lbl_sizepolicy)
        self.scan_size_spinBox_c = QSpinBox()
        self.scan_size_spinBox_c.setAlignment(Qt.AlignCenter)
        col_wdg_lay.addWidget(col_label)
        col_wdg_lay.addWidget(self.scan_size_spinBox_c)

        # overlay
        self.ovl_wdg = QWidget()
        ovl_wdg_lay = QHBoxLayout()
        ovl_wdg_lay.setSpacing(0)
        ovl_wdg_lay.setContentsMargins(0, 0, 0, 0)
        self.ovl_wdg.setLayout(ovl_wdg_lay)
        overlap_label = QLabel(text="Overlap (%):")
        overlap_label.setSizePolicy(lbl_sizepolicy)
        self.ovelap_spinBox = QSpinBox()
        self.ovelap_spinBox.setAlignment(Qt.AlignCenter)
        ovl_wdg_lay.addWidget(overlap_label)
        ovl_wdg_lay.addWidget(self.ovelap_spinBox)

        group_layout.addWidget(self.row_wdg)
        group_layout.addWidget(self.col_wdg)
        group_layout.addWidget(self.ovl_wdg)
        return group

    def _create_channel_group(self):

        group = QGroupBox(title="Channels")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        group_layout = QGridLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # table
        self.channel_explorer_tableWidget = QTableWidget()
        hdr = self.channel_explorer_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.channel_explorer_tableWidget.setTabKeyNavigation(True)
        self.channel_explorer_tableWidget.setColumnCount(2)
        self.channel_explorer_tableWidget.setRowCount(0)
        self.channel_explorer_tableWidget.setHorizontalHeaderLabels(
            ["Channel", "Exp. Time (ms)"]
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

    def _create_save_group(self):
        group = QGroupBox(title="Save Scan")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group.setCheckable(True)
        group.setChecked(False)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
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
        self.dir_explorer_lineEdit = QLineEdit()
        self.browse_save_explorer_Button = QPushButton(text="...")
        self.browse_save_explorer_Button.setSizePolicy(btn_sizepolicy)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_explorer_lineEdit)
        dir_group_layout.addWidget(self.browse_save_explorer_Button)

        # filename
        fname_group = QWidget()
        fname_group_layout = QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(10, 10, 10, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_explorer_lineEdit = QLineEdit()
        self.fname_explorer_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_explorer_lineEdit)

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)

        return group

    def _create_start_stop_buttons(self):
        wdg = QWidget()
        wdg.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)
        btn_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        icon_size = 40
        self.start_scan_Button = QPushButton(text="Start Scan")
        self.start_scan_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.start_scan_Button.setSizePolicy(btn_sizepolicy)
        self.start_scan_Button.setIcon(icon(MDI6.play, color=(0, 255, 0)))
        self.start_scan_Button.setIconSize(QSize(icon_size, icon_size))
        self.stop_scan_Button = QPushButton(text="Stop Scan")
        self.stop_scan_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.stop_scan_Button.setSizePolicy(btn_sizepolicy)
        self.stop_scan_Button.setIcon(icon(MDI6.stop, color="magenta"))
        self.stop_scan_Button.setIconSize(QSize(icon_size, icon_size))
        wdg_layout.addWidget(self.start_scan_Button)
        wdg_layout.addWidget(self.stop_scan_Button)

        return wdg

    def _create_move_to_pos(self):
        group = QGroupBox(title="Move to Position")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QHBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        self.move_to_Button = QPushButton(text="Move to")
        self.move_to_Button.setSizePolicy(
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        )

        self.x_lineEdit = QLineEdit()
        self.x_lineEdit.setReadOnly(True)
        self.x_lineEdit.setAlignment(QtCore.Qt.AlignCenter)

        self.y_lineEdit = QLineEdit()
        self.y_lineEdit.setReadOnly(True)
        self.y_lineEdit.setAlignment(QtCore.Qt.AlignCenter)

        group_layout.addWidget(self.move_to_Button)
        group_layout.addWidget(self.x_lineEdit)
        group_layout.addWidget(self.y_lineEdit)

        return group
