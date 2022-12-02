from pathlib import Path
from typing import Optional, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .._mda_meta import SEQUENCE_META, SequenceMeta


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: Optional[QWidget] = None, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.save_groupbox = self._create_save_group()
        v_layout = cast(QVBoxLayout, self._wdg.layout())
        v_layout.insertWidget(0, self.save_groupbox)

        self.channel_groupbox.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_groupbox.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)

        self.browse_save_button.clicked.connect(self._set_multi_d_acq_dir)
        self.save_groupbox.toggled.connect(self._toggle_checkbox_save_pos)
        self.stage_pos_groupbox.toggled.connect(self._toggle_checkbox_save_pos)

        self.stage_pos_groupbox.add_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )
        self.stage_pos_groupbox.remove_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )
        self.stage_pos_groupbox.clear_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )

        self.channel_groupbox.channel_tableWidget.model().rowsRemoved.connect(
            self._toggle_split_channel
        )

    def _create_save_group(self) -> QGroupBox:
        group = QGroupBox(title="Save MultiD Acquisition")
        group.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
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
        sizepolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        min_lbl_size = 80
        dir_lbl = QLabel(text="Directory:")
        dir_lbl.setMinimumWidth(min_lbl_size)
        dir_lbl.setSizePolicy(sizepolicy)
        self.dir_lineEdit = QLineEdit()
        self.browse_save_button = QPushButton(text="...")
        self.browse_save_button.setSizePolicy(sizepolicy)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_lineEdit)
        dir_group_layout.addWidget(self.browse_save_button)

        # filename
        fname_group = QWidget()
        fname_group_layout = QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(sizepolicy)
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

    def _set_multi_d_acq_dir(self) -> None:
        # set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.FileMode.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _toggle_split_channel(self) -> None:
        if self.channel_groupbox.channel_tableWidget.rowCount() <= 1:
            self.checkBox_split_channels.setChecked(False)

    def _toggle_checkbox_save_pos(self) -> None:
        if (
            self.stage_pos_groupbox.isChecked()
            and self.stage_pos_groupbox.stage_tableWidget.rowCount() > 0
        ):
            self.checkBox_save_pos.setEnabled(True)

        else:
            self.checkBox_save_pos.setCheckState(Qt.CheckState.Unchecked)
            self.checkBox_save_pos.setEnabled(False)

    def _on_run_clicked(self) -> None:
        """Run the MDA sequence experiment."""

        # construct a `useq.MDASequence` object from the values inserted in the widget
        experiment = self.get_state()

        SEQUENCE_META[experiment] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            should_save=self.save_groupbox.isChecked(),
            file_name=self.fname_lineEdit.text(),
            save_dir=self.dir_lineEdit.text()
            or str(Path(__file__).parent.parent.parent),
            save_pos=self.checkBox_save_pos.isChecked(),
        )

        # run the MDA experiment asynchronously
        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return
