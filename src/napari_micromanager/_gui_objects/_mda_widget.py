from __future__ import annotations

from pathlib import Path
from typing import cast

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QGridLayout, QSizePolicy, QVBoxLayout, QWidget
from useq import MDASequence

from ._save_widget import SaveWidget


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self._save_groupbox = SaveWidget()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)

        v_layout = cast(QVBoxLayout, self.layout())
        v_layout.insertWidget(0, self._save_groupbox)

        self.channel_groupbox.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_groupbox.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)

        # TODO: stage_pos_groupbox should have a valueChanged signal
        # and that should be connected to _toggle_checkbox_save_pos
        self._save_groupbox.toggled.connect(self._toggle_checkbox_save_pos)
        self.position_groupbox.valueChanged.connect(self._toggle_checkbox_save_pos)
        self.channel_groupbox.valueChanged.connect(self._toggle_split_channel)

    def _toggle_split_channel(self) -> None:
        if not self.channel_groupbox.value():
            self.checkBox_split_channels.setChecked(False)

    def _toggle_checkbox_save_pos(self) -> None:
        if (
            self.position_groupbox.isChecked()
            and len(self.position_groupbox.value()) > 0
        ):
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
