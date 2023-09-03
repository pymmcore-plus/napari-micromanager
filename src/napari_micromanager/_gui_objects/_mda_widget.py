from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pymmcore_widgets import MDAWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

from ._save_widget import SaveWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)
        # add save widget
        v_layout = cast(QVBoxLayout, self._central_widget.layout())
        self._save_groupbox = SaveWidget()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)
        self._save_groupbox.toggled.connect(self._on_save_toggled)
        self._save_groupbox._directory.textChanged.connect(self._on_save_toggled)
        self._save_groupbox._fname.textChanged.connect(self._on_save_toggled)
        v_layout.insertWidget(0, self._save_groupbox)

        # add split channel checkbox
        self.channel_widget.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_widget.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)
        self.channel_widget.valueChanged.connect(self._toggle_split_channel)

    def _toggle_split_channel(self) -> None:
        if (
            not self.channel_widget.value()
            or self.channel_widget._table.rowCount() == 1
        ):
            self.checkBox_split_channels.setChecked(False)

    def _on_save_toggled(self) -> None:
        if self.position_widget.value():
            self._save_groupbox._split_pos_checkbox.setEnabled(True)

        else:
            self._save_groupbox._split_pos_checkbox.setCheckState(
                Qt.CheckState.Unchecked
            )
            self._save_groupbox._split_pos_checkbox.setEnabled(False)

    def get_state(self) -> MDASequence:
        sequence = cast(MDASequence, super().get_state())
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            **self._save_groupbox.get_state(),
        )
        return sequence

    def set_state(self, state: dict | MDASequence | str | Path) -> None:
        super().set_state(state)
        meta = None
        if isinstance(state, dict):
            meta = state.get("metadata", {}).get(SEQUENCE_META_KEY)
        elif isinstance(state, MDASequence):
            meta = state.metadata.get(SEQUENCE_META_KEY)

        if meta is None:
            return
        if not isinstance(meta, SequenceMeta):
            raise TypeError(f"Expected {SequenceMeta}, got {type(meta)}")
        if meta.mode.lower() != "mda":
            raise ValueError(f"Expected mode 'mda', got {meta.mode}")

        self.checkBox_split_channels.setChecked(meta.split_channels)
        self._save_groupbox.set_state(meta)

    def _on_run_clicked(self) -> None:
        if (
            self._save_groupbox.isChecked()
            and not self._save_groupbox._directory.text()
        ):
            warnings.warn("Select a directory to save the data.", stacklevel=2)
            return

        if not Path(self._save_groupbox._directory.text()).exists():
            if self._create_new_folder():
                Path(self._save_groupbox._directory.text()).mkdir(parents=True)
            else:
                return

        super()._on_run_clicked()

    def _create_new_folder(self) -> bool:
        """Create a QMessageBox to ask to create directory if it doesn't exist."""
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Create Directory")
        msgBox.setIcon(QMessageBox.Icon.Question)
        msgBox.setText(
            f"Directory {self._save_groupbox._directory.text()} "
            "does not exist. Create it?"
        )
        msgBox.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        return bool(msgBox.exec() == QMessageBox.StandardButton.Ok)
