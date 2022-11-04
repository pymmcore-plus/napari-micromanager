from pathlib import Path
from typing import Optional, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MultiDWidget
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, Signal
from useq import MDASequence

from .._mda_meta import SEQUENCE_META, SequenceMeta


class MDAWidget(MultiDWidget):
    """Main napari-micromanager GUI."""

    metadataInfo = Signal(SequenceMeta, MDASequence)

    def __init__(
        self,
        parent: Optional[QtW.QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.save_groupBox = self._create_save_group()
        v_layout = cast(QtW.QVBoxLayout, self._wdg.layout())
        v_layout.insertWidget(0, self.save_groupBox)

        self.checkBox_split_channels = QtW.QCheckBox(text="Split Channels")
        g_layout = cast(QtW.QGridLayout, self.channel_groupBox.layout())
        g_layout.addWidget(self.checkBox_split_channels, 3, 0, 1, 1)

        self.run_Button.clicked.connect(self._send_meta)

        self.browse_save_Button.clicked.connect(self._set_multi_d_acq_dir)
        self.save_groupBox.toggled.connect(self._toggle_checkbox_save_pos)
        self.stage_pos_groupBox.toggled.connect(self._toggle_checkbox_save_pos)

        self.add_pos_Button.clicked.connect(self._toggle_checkbox_save_pos)
        self.remove_pos_Button.clicked.connect(self._toggle_checkbox_save_pos)
        self.clear_pos_Button.clicked.connect(self._toggle_checkbox_save_pos)

    def _create_save_group(self) -> QtW.QGroupBox:
        group = QtW.QGroupBox(title="Save MultiD Acquisition")
        group.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Fixed)
        )
        group.setCheckable(True)
        group.setChecked(False)
        group_layout = QtW.QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # directory
        dir_group = QtW.QWidget()
        dir_group_layout = QtW.QHBoxLayout()
        dir_group_layout.setSpacing(5)
        dir_group_layout.setContentsMargins(0, 10, 0, 5)
        dir_group.setLayout(dir_group_layout)
        sizepolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        min_lbl_size = 80
        dir_lbl = QtW.QLabel(text="Directory:")
        dir_lbl.setMinimumWidth(min_lbl_size)
        dir_lbl.setSizePolicy(sizepolicy)
        self.dir_lineEdit = QtW.QLineEdit()
        self.browse_save_Button = QtW.QPushButton(text="...")
        self.browse_save_Button.setSizePolicy(sizepolicy)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_lineEdit)
        dir_group_layout.addWidget(self.browse_save_Button)

        # filename
        fname_group = QtW.QWidget()
        fname_group_layout = QtW.QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QtW.QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(sizepolicy)
        self.fname_lineEdit = QtW.QLineEdit()
        self.fname_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_lineEdit)

        # checkbox
        self.checkBox_save_pos = QtW.QCheckBox(
            text="Save XY Positions in separate files (ImageJ compatibility)"
        )

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)
        group_layout.addWidget(self.checkBox_save_pos)

        return group

    def _set_multi_d_acq_dir(self) -> None:
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _toggle_checkbox_save_pos(self) -> None:
        if (
            self.stage_pos_groupBox.isChecked()
            and self.stage_tableWidget.rowCount() > 0
        ):
            self.checkBox_save_pos.setEnabled(True)

        else:
            self.checkBox_save_pos.setCheckState(Qt.CheckState.Unchecked)
            self.checkBox_save_pos.setEnabled(False)

    def _send_meta(self) -> None:
        sequence = self.get_state()
        SEQUENCE_META[sequence] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            should_save=self.save_groupBox.isChecked(),
            file_name=self.fname_lineEdit.text(),
            save_dir=self.dir_lineEdit.text()
            or str(Path(__file__).parent.parent.parent),
            save_pos=self.checkBox_save_pos.isChecked(),
        )
        self.metadataInfo.emit(SEQUENCE_META[sequence], self.get_state())


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = MDAWidget()
    win.show()
    sys.exit(app.exec_())
