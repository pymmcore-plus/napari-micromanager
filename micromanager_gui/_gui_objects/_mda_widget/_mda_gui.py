from typing import Optional

from fonticon_mdi6 import MDI6
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
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
from superqt.fonticon import icon


class MultiDWidgetGui(QWidget):
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

        # acq order and buttons wdg
        self.bottom_wdg = self._create_bottom_wdg()
        self.layout().addWidget(self.bottom_wdg)

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

        return wdg

    def _create_save_group(self):
        group = QGroupBox(title="Save MultiD Acquisition")
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
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_lineEdit = QLineEdit()
        self.fname_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_lineEdit)

        # checkbox
        self.checkBox_save_pos = QCheckBox(
            text="Save XY Positions in separate files (ImageJ compatibility)"
        )

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)
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
        self.channel_tableWidget = QTableWidget()
        self.channel_tableWidget.setMinimumHeight(90)
        hdr = self.channel_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.channel_tableWidget.verticalHeader().setVisible(False)
        self.channel_tableWidget.setTabKeyNavigation(True)
        self.channel_tableWidget.setColumnCount(2)
        self.channel_tableWidget.setRowCount(0)
        self.channel_tableWidget.setHorizontalHeaderLabels(
            ["Channel", "Exposure Time (ms)"]
        )
        group_layout.addWidget(self.channel_tableWidget, 0, 0, 3, 1)

        # buttons
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_size = 100
        self.add_ch_Button = QPushButton(text="Add")
        self.add_ch_Button.setMinimumWidth(min_size)
        self.add_ch_Button.setSizePolicy(btn_sizepolicy)
        self.remove_ch_Button = QPushButton(text="Remove")
        self.remove_ch_Button.setMinimumWidth(min_size)
        self.remove_ch_Button.setSizePolicy(btn_sizepolicy)
        self.clear_ch_Button = QPushButton(text="Clear")
        self.clear_ch_Button.setMinimumWidth(min_size)
        self.clear_ch_Button.setSizePolicy(btn_sizepolicy)

        # checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")

        group_layout.addWidget(self.add_ch_Button, 0, 1, 1, 1)
        group_layout.addWidget(self.remove_ch_Button, 1, 1, 1, 2)
        group_layout.addWidget(self.clear_ch_Button, 2, 1, 1, 2)
        group_layout.addWidget(self.checkBox_split_channels, 3, 0, 1, 1)

        return group

    def _create_time_group(self):
        group = QGroupBox(title="Time")
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
        group = QGroupBox(title="Z Stacks")
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
        group = QGroupBox(title="Stage Positions (double-click to move to position)")
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
        self.stage_tableWidget.setMinimumHeight(90)
        hdr = self.stage_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.stage_tableWidget.verticalHeader().setVisible(False)
        self.stage_tableWidget.setTabKeyNavigation(True)
        self.stage_tableWidget.setColumnCount(3)
        self.stage_tableWidget.setRowCount(0)
        self.stage_tableWidget.setHorizontalHeaderLabels(["X", "Y", "Z"])
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

    def _create_bottom_wdg(self):

        wdg = QWidget()
        wdg.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        wdg_layout = QHBoxLayout()
        wdg_layout.setAlignment(Qt.AlignVCenter)
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(10, 15, 10, 10)
        wdg.setLayout(wdg_layout)

        acq_wdg = QWidget()
        acq_wdg_layout = QHBoxLayout()
        acq_wdg_layout.setSpacing(0)
        acq_wdg_layout.setContentsMargins(0, 0, 0, 0)
        acq_wdg.setLayout(acq_wdg_layout)
        acquisition_order_label = QLabel(text="Acquisition Order:")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        acquisition_order_label.setSizePolicy(lbl_sizepolicy)
        self.acquisition_order_comboBox = QComboBox()
        self.acquisition_order_comboBox.setMinimumWidth(100)
        self.acquisition_order_comboBox.addItems(["tpzc", "tpcz", "ptzc", "ptcz"])
        acq_wdg_layout.addWidget(acquisition_order_label)
        acq_wdg_layout.addWidget(self.acquisition_order_comboBox)

        btn_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        min_width = 130
        icon_size = 40
        self.run_Button = QPushButton(text="Run")
        self.run_Button.setMinimumWidth(min_width)
        self.run_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.run_Button.setSizePolicy(btn_sizepolicy)
        self.run_Button.setIcon(icon(MDI6.play, color=(0, 255, 0)))
        self.run_Button.setIconSize(QSize(icon_size, icon_size))
        self.pause_Button = QPushButton("Pause")
        self.pause_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.pause_Button.setSizePolicy(btn_sizepolicy)
        self.pause_Button.setIcon(icon(MDI6.pause, color="green"))
        self.pause_Button.setIconSize(QSize(icon_size, icon_size))
        self.cancel_Button = QPushButton("Cancel")
        self.cancel_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.cancel_Button.setSizePolicy(btn_sizepolicy)
        self.cancel_Button.setIcon(icon(MDI6.stop, color="magenta"))
        self.cancel_Button.setIconSize(QSize(icon_size, icon_size))

        spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Expanding)

        wdg_layout.addWidget(acq_wdg)
        wdg_layout.addItem(spacer)
        wdg_layout.addWidget(self.run_Button)
        wdg_layout.addWidget(self.pause_Button)
        wdg_layout.addWidget(self.cancel_Button)

        return wdg


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = MultiDWidgetGui()
    win.show()
    sys.exit(app.exec_())
