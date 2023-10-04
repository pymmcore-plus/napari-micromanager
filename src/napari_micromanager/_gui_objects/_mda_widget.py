from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)

        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        ch_layout.addWidget(self.checkBox_split_channels)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = cast(MDASequence, super().value())
        save_info = self.save_info.value()

        # this is to avoid the AttributeError the first time the MDAWidget is called
        try:
            split_channels = bool(
                self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
            )
        except AttributeError:
            split_channels = False

        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=split_channels,
            save_dir=save_info.get("save_dir", ""),
            file_name=save_info.get("save_name", ""),
            # this will be removed in the next PR where we will use the pymmcore-plus
            # writers
            should_save=bool(
                save_info.get("save_dir", "") and save_info.get("save_name", "")
            ),
        )
        return sequence

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        meta = value.metadata.get(SEQUENCE_META_KEY)
        if meta and not isinstance(meta, SequenceMeta):
            raise TypeError(f"Expected {SequenceMeta}, got {type(meta)}")
        super().setValue(value)
