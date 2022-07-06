from typing import Optional

from fonticon_mdi6 import MDI6
from qtpy import QtCore
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from superqt import QCollapsible
from superqt.fonticon import icon


class ExplorerGui(QWidget):
    """Just the UI of the explorer widget. Runtime logic in MMExploreSample."""

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
        wdg_layout.setSpacing(15)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)

        self.save_explorer_groupBox = self._create_save_group()
        wdg_layout.addWidget(self.save_explorer_groupBox)

        self.scan_props = self._create_row_cols_overlap_group()
        wdg_layout.addWidget(self.scan_props)

        self.channel_explorer_groupBox = self._create_channel_group()
        wdg_layout.addWidget(self.channel_explorer_groupBox)

        self.time_coll_group = self._create_time_collapsible_groups()
        wdg_layout.addWidget(self.time_coll_group)

        self.stack_coll_group = self._create_stack_collapsible_groups()
        wdg_layout.addWidget(self.stack_coll_group)

        self.positions_coll_group = self._create_positions_collapsible_groups()
        wdg_layout.addWidget(self.positions_coll_group)

        self.checkbox = self._create_display_checkbox()
        wdg_layout.addWidget(self.checkbox)

        self.btns = self._create_start_stop_buttons()
        wdg_layout.addWidget(self.btns)

        self.move_to_pos = self._create_move_to_pos()
        wdg_layout.addWidget(self.move_to_pos)

        spacer = QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        wdg_layout.addItem(spacer)

        return wdg

    def _create_row_cols_overlap_group(self):
        group = QGroupBox(title="Grid Parameters")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 20, 10, 20)
        group.setLayout(group_layout)

        fix_lbl_size = 80
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # row
        self.row_wdg = QWidget()
        row_wdg_lay = QHBoxLayout()
        row_wdg_lay.setSpacing(0)
        row_wdg_lay.setContentsMargins(0, 0, 0, 0)
        self.row_wdg.setLayout(row_wdg_lay)
        row_label = QLabel(text="Rows:")
        row_label.setMaximumWidth(fix_lbl_size)
        row_label.setSizePolicy(lbl_sizepolicy)
        self.scan_size_spinBox_r = QSpinBox()
        self.scan_size_spinBox_r.setMinimum(1)
        self.scan_size_spinBox_r.setAlignment(Qt.AlignCenter)
        row_wdg_lay.addWidget(row_label)
        row_wdg_lay.addWidget(self.scan_size_spinBox_r)

        # col
        self.col_wdg = QWidget()
        col_wdg_lay = QHBoxLayout()
        col_wdg_lay.setSpacing(0)
        col_wdg_lay.setContentsMargins(0, 0, 0, 0)
        self.col_wdg.setLayout(col_wdg_lay)
        col_label = QLabel(text="Columns:")
        col_label.setMaximumWidth(fix_lbl_size)
        col_label.setSizePolicy(lbl_sizepolicy)
        self.scan_size_spinBox_c = QSpinBox()
        self.scan_size_spinBox_c.setSizePolicy
        self.scan_size_spinBox_c.setMinimum(1)
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
        overlap_label.setMaximumWidth(fix_lbl_size)
        overlap_label.setSizePolicy(lbl_sizepolicy)
        self.ovelap_spinBox = QSpinBox()
        self.ovelap_spinBox.setAlignment(Qt.AlignCenter)
        ovl_wdg_lay.addWidget(overlap_label)
        ovl_wdg_lay.addWidget(self.ovelap_spinBox)

        group_layout.addWidget(self.row_wdg, 0, 0)
        group_layout.addWidget(self.col_wdg, 1, 0)
        group_layout.addWidget(self.ovl_wdg, 0, 1)
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
        dir_group_layout.setContentsMargins(0, 10, 0, 5)
        dir_group.setLayout(dir_group_layout)
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_lbl_size = 80
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
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name:")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_explorer_lineEdit = QLineEdit()
        self.fname_explorer_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_explorer_lineEdit)

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)

        return group

    def _create_time_collapsible_groups(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(0)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        group_time = QGroupBox()
        group_time_layout = QVBoxLayout()
        group_time_layout.setSpacing(0)
        group_time_layout.setContentsMargins(0, 0, 0, 0)
        group_time.setLayout(group_time_layout)
        coll_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.time_coll = QCollapsible(title="Time")
        self.time_coll.setSizePolicy(coll_sizepolicy)
        self.time_coll.layout().setSpacing(5)
        self.time_coll.layout().setContentsMargins(0, 0, 5, 5)
        self.time_groupBox = self._create_time_group()
        self.time_coll.addWidget(self.time_groupBox)
        group_time_layout.addWidget(self.time_coll)

        wdg_layout.addWidget(group_time)

        return wdg

    def _create_stack_collapsible_groups(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(0)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        group_stack = QGroupBox()
        group_stack_layout = QVBoxLayout()
        group_stack_layout.setSpacing(0)
        group_stack_layout.setContentsMargins(0, 0, 0, 0)
        group_stack.setLayout(group_stack_layout)
        coll_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stack_coll = QCollapsible(title="Z Stack")
        self.stack_coll.setSizePolicy(coll_sizepolicy)
        self.stack_coll.layout().setSpacing(5)
        self.stack_coll.layout().setContentsMargins(0, 0, 5, 5)
        self.stack_groupBox = self._create_stack_groupBox()
        self.stack_coll.addWidget(self.stack_groupBox)
        group_stack_layout.addWidget(self.stack_coll)

        wdg_layout.addWidget(group_stack)

        return wdg

    def _create_positions_collapsible_groups(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(0)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        group_pos = QGroupBox()
        group_pos_layout = QVBoxLayout()
        group_pos_layout.setSpacing(0)
        group_pos_layout.setContentsMargins(0, 0, 0, 0)
        group_pos.setLayout(group_pos_layout)
        coll_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.pos_coll = QCollapsible(title="Grid Starting Positions")
        self.pos_coll.setSizePolicy(coll_sizepolicy)
        self.pos_coll.layout().setSpacing(5)
        self.pos_coll.layout().setContentsMargins(0, 0, 5, 5)
        self.stage_pos_groupBox = self._create_stage_pos_groupBox()
        self.pos_coll.addWidget(self.stage_pos_groupBox)
        group_pos_layout.addWidget(self.pos_coll)

        wdg_layout.addWidget(group_pos)

        return wdg

    def _create_time_group(self):
        group = QGroupBox()
        group.setCheckable(True)
        group.setChecked(False)
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QHBoxLayout()
        group_layout.setSpacing(20)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Timepoints
        wdg = QWidget()
        wdg_lay = QHBoxLayout()
        wdg_lay.setSpacing(5)
        wdg_lay.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_lay)
        lbl = QLabel(text="Timepoints:")
        lbl.setSizePolicy(lbl_sizepolicy)
        self.timepoints_spinBox = QSpinBox()
        self.timepoints_spinBox.setMinimum(1)
        self.timepoints_spinBox.setMaximum(10000)
        self.timepoints_spinBox.setAlignment(Qt.AlignCenter)
        wdg_lay.addWidget(lbl)
        wdg_lay.addWidget(self.timepoints_spinBox)
        group_layout.addWidget(wdg)

        # Interval
        wdg1 = QWidget()
        wdg1_lay = QHBoxLayout()
        wdg1_lay.setSpacing(5)
        wdg1_lay.setContentsMargins(0, 0, 0, 0)
        wdg1.setLayout(wdg1_lay)
        lbl1 = QLabel(text="Interval:")
        lbl1.setSizePolicy(lbl_sizepolicy)
        self.interval_spinBox = QSpinBox()
        self.interval_spinBox.setMinimum(0)
        self.interval_spinBox.setMaximum(10000)
        self.interval_spinBox.setAlignment(Qt.AlignCenter)
        wdg1_lay.addWidget(lbl1)
        wdg1_lay.addWidget(self.interval_spinBox)
        group_layout.addWidget(wdg1)

        self.time_comboBox = QComboBox()
        self.time_comboBox.setSizePolicy(
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        )
        self.time_comboBox.addItems(["ms", "sec", "min"])
        group_layout.addWidget(self.time_comboBox)

        return group

    def _create_stack_groupBox(self):
        group = QGroupBox()
        group.setCheckable(True)
        group.setChecked(False)
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # tab
        self.z_tabWidget = QTabWidget()
        z_tab_layout = QVBoxLayout()
        z_tab_layout.setSpacing(0)
        z_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.z_tabWidget.setLayout(z_tab_layout)
        group_layout.addWidget(self.z_tabWidget)

        # top bottom
        tb = QWidget()
        tb_layout = QGridLayout()
        tb_layout.setContentsMargins(10, 10, 10, 10)
        tb.setLayout(tb_layout)

        self.set_top_Button = QPushButton(text="Set Top")
        self.set_bottom_Button = QPushButton(text="Set Bottom")

        lbl_range_tb = QLabel(text="Range (µm):")
        lbl_range_tb.setAlignment(Qt.AlignCenter)

        self.z_top_doubleSpinBox = QDoubleSpinBox()
        self.z_top_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.z_top_doubleSpinBox.setMinimum(0.0)
        self.z_top_doubleSpinBox.setMaximum(100000)
        self.z_top_doubleSpinBox.setDecimals(2)

        self.z_bottom_doubleSpinBox = QDoubleSpinBox()
        self.z_bottom_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.z_bottom_doubleSpinBox.setMinimum(0.0)
        self.z_bottom_doubleSpinBox.setMaximum(100000)
        self.z_bottom_doubleSpinBox.setDecimals(2)

        self.z_range_topbottom_doubleSpinBox = QDoubleSpinBox()
        self.z_range_topbottom_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.z_range_topbottom_doubleSpinBox.setMaximum(10000000)
        self.z_range_topbottom_doubleSpinBox.setButtonSymbols(
            QAbstractSpinBox.NoButtons
        )
        self.z_range_topbottom_doubleSpinBox.setReadOnly(True)

        tb_layout.addWidget(self.set_top_Button, 0, 0)
        tb_layout.addWidget(self.z_top_doubleSpinBox, 1, 0)
        tb_layout.addWidget(self.set_bottom_Button, 0, 1)
        tb_layout.addWidget(self.z_bottom_doubleSpinBox, 1, 1)
        tb_layout.addWidget(lbl_range_tb, 0, 2)
        tb_layout.addWidget(self.z_range_topbottom_doubleSpinBox, 1, 2)

        self.z_tabWidget.addTab(tb, "TopBottom")

        # range around
        ra = QWidget()
        ra_layout = QHBoxLayout()
        ra_layout.setSpacing(10)
        ra_layout.setContentsMargins(10, 10, 10, 10)
        ra.setLayout(ra_layout)

        lbl_range_ra = QLabel(text="Range (µm):")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lbl_range_ra.setSizePolicy(lbl_sizepolicy)

        self.zrange_spinBox = QSpinBox()
        self.zrange_spinBox.setValue(5)
        self.zrange_spinBox.setAlignment(Qt.AlignCenter)
        self.zrange_spinBox.setMaximum(100000)

        self.range_around_label = QLabel(text="-2.5 µm <- z -> +2.5 µm")
        self.range_around_label.setAlignment(Qt.AlignCenter)

        ra_layout.addWidget(lbl_range_ra)
        ra_layout.addWidget(self.zrange_spinBox)
        ra_layout.addWidget(self.range_around_label)

        self.z_tabWidget.addTab(ra, "RangeAround")

        # above below wdg
        ab = QWidget()
        ab_layout = QGridLayout()
        ab_layout.setContentsMargins(10, 0, 10, 15)
        ab.setLayout(ab_layout)

        lbl_above = QLabel(text="Above (µm):")
        lbl_above.setAlignment(Qt.AlignCenter)
        self.above_doubleSpinBox = QDoubleSpinBox()
        self.above_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.above_doubleSpinBox.setMinimum(0.05)
        self.above_doubleSpinBox.setMaximum(10000)
        self.above_doubleSpinBox.setSingleStep(0.5)
        self.above_doubleSpinBox.setDecimals(2)

        lbl_below = QLabel(text="Below (µm):")
        lbl_below.setAlignment(Qt.AlignCenter)
        self.below_doubleSpinBox = QDoubleSpinBox()
        self.below_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.below_doubleSpinBox.setMinimum(0.05)
        self.below_doubleSpinBox.setMaximum(10000)
        self.below_doubleSpinBox.setSingleStep(0.5)
        self.below_doubleSpinBox.setDecimals(2)

        lbl_range = QLabel(text="Range (µm):")
        lbl_range.setAlignment(Qt.AlignCenter)
        self.z_range_abovebelow_doubleSpinBox = QDoubleSpinBox()
        self.z_range_abovebelow_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.z_range_abovebelow_doubleSpinBox.setMaximum(10000000)
        self.z_range_abovebelow_doubleSpinBox.setButtonSymbols(
            QAbstractSpinBox.NoButtons
        )
        self.z_range_abovebelow_doubleSpinBox.setReadOnly(True)

        ab_layout.addWidget(lbl_above, 0, 0)
        ab_layout.addWidget(self.above_doubleSpinBox, 1, 0)
        ab_layout.addWidget(lbl_below, 0, 1)
        ab_layout.addWidget(self.below_doubleSpinBox, 1, 1)
        ab_layout.addWidget(lbl_range, 0, 2)
        ab_layout.addWidget(self.z_range_abovebelow_doubleSpinBox, 1, 2)

        self.z_tabWidget.addTab(ab, "AboveBelow")

        # step size wdg
        step_wdg = QWidget()
        step_wdg_layout = QHBoxLayout()
        step_wdg_layout.setSpacing(15)
        step_wdg_layout.setContentsMargins(0, 10, 0, 0)
        step_wdg.setLayout(step_wdg_layout)

        s = QWidget()
        s_layout = QHBoxLayout()
        s_layout.setSpacing(0)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s.setLayout(s_layout)
        lbl = QLabel(text="Step Size (µm):")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lbl.setSizePolicy(lbl_sizepolicy)
        self.step_size_doubleSpinBox = QDoubleSpinBox()
        self.step_size_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.step_size_doubleSpinBox.setMinimum(0.05)
        self.step_size_doubleSpinBox.setMaximum(10000)
        self.step_size_doubleSpinBox.setSingleStep(0.5)
        self.step_size_doubleSpinBox.setDecimals(2)
        s_layout.addWidget(lbl)
        s_layout.addWidget(self.step_size_doubleSpinBox)

        self.n_images_label = QLabel(text="Number of Images:")

        step_wdg_layout.addWidget(s)
        step_wdg_layout.addWidget(self.n_images_label)
        group_layout.addWidget(step_wdg)

        return group

    def _create_stage_pos_groupBox(self):
        group = QGroupBox(title="(double-click to move to position)")
        group.setCheckable(True)
        group.setChecked(False)
        group.setMinimumHeight(230)
        group_layout = QGridLayout()
        group_layout.setHorizontalSpacing(15)
        group_layout.setVerticalSpacing(0)
        group_layout.setContentsMargins(10, 0, 10, 0)
        group.setLayout(group_layout)

        # table
        self.stage_tableWidget = QTableWidget()
        self.stage_tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stage_tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stage_tableWidget.setMinimumHeight(90)
        hdr = self.stage_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.stage_tableWidget.verticalHeader().setVisible(False)
        self.stage_tableWidget.setTabKeyNavigation(True)
        self.stage_tableWidget.setColumnCount(4)
        self.stage_tableWidget.setRowCount(0)
        self.stage_tableWidget.setHorizontalHeaderLabels(["Grid #", "X", "Y", "Z"])
        group_layout.addWidget(self.stage_tableWidget, 0, 0, 3, 1)

        # buttons
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_size = 100
        self.add_pos_Button = QPushButton(text="Add")
        self.add_pos_Button.setMinimumWidth(min_size)
        self.add_pos_Button.setSizePolicy(btn_sizepolicy)
        self.remove_pos_Button = QPushButton(text="Remove")
        self.remove_pos_Button.setMinimumWidth(min_size)
        self.remove_pos_Button.setSizePolicy(btn_sizepolicy)
        self.clear_pos_Button = QPushButton(text="Clear")
        self.clear_pos_Button.setMinimumWidth(min_size)
        self.clear_pos_Button.setSizePolicy(btn_sizepolicy)

        group_layout.addWidget(self.add_pos_Button, 0, 1, 1, 1)
        group_layout.addWidget(self.remove_pos_Button, 1, 1, 1, 2)
        group_layout.addWidget(self.clear_pos_Button, 2, 1, 1, 2)

        return group

    def _create_display_checkbox(self):
        group = QGroupBox()
        group.setChecked(False)
        group_layout = QHBoxLayout()
        group_layout.setSpacing(7)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        fixed_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        lbl = QLabel(text="Display as:")
        lbl.setSizePolicy(fixed_policy)

        self.display_checkbox = QCheckBox(text="layers translation")
        self.display_checkbox.setSizePolicy(fixed_policy)
        self.display_checkbox.setChecked(True)
        self.display_checkbox_real = QCheckBox(text="...in stage coords")
        self.display_checkbox_real.setSizePolicy(fixed_policy)
        self.multid_stack_checkbox = QCheckBox(text="multiD stack")
        self.multid_stack_checkbox.setSizePolicy(fixed_policy)

        self.display_checkbox.toggled.connect(self._toggle_checkboxes)
        self.display_checkbox.toggled.connect(self._toggle_display_checkboxes)
        self.multid_stack_checkbox.toggled.connect(self._toggle_checkboxes)

        group_layout.addWidget(lbl)
        group_layout.addWidget(self.display_checkbox)
        group_layout.addWidget(self.display_checkbox_real)
        group_layout.addWidget(self.multid_stack_checkbox)

        return group

    def _toggle_checkboxes(self, state: bool) -> None:
        if self.sender() == self.multid_stack_checkbox:
            self.display_checkbox.setChecked(not state)

        elif self.sender() == self.display_checkbox:
            self.multid_stack_checkbox.setChecked(not state)

    def _toggle_display_checkboxes(self, state: bool) -> None:
        self.display_checkbox_real.setEnabled(state)
        self.display_checkbox_real.setChecked(False)

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
        self.start_scan_Button.setIcon(
            icon(MDI6.play_circle_outline, color=(0, 255, 0))
        )
        self.start_scan_Button.setIconSize(QSize(icon_size, icon_size))
        self.stop_scan_Button = QPushButton(text="Stop Scan")
        self.stop_scan_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.stop_scan_Button.setSizePolicy(btn_sizepolicy)
        self.stop_scan_Button.setIcon(icon(MDI6.stop_circle_outline, color="magenta"))
        self.stop_scan_Button.setIconSize(QSize(icon_size, icon_size))
        wdg_layout.addWidget(self.start_scan_Button)
        wdg_layout.addWidget(self.stop_scan_Button)

        return wdg

    def _create_move_to_pos(self):
        group = QGroupBox(title="Move to Position")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group_layout = QHBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 20, 10, 20)
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


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = ExplorerGui()
    win.show()
    sys.exit(app.exec_())
