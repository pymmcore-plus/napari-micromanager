from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence


MMCORE_WIDGETS_META = "pymmcore_widgets"
NAPARI_MM_META = "napari_micromanager"


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout.addWidget(self.checkBox_split_channels)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = super().value()
        split = self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
        sequence.metadata[NAPARI_MM_META] = {"split_channels": split}
        return sequence  # type: ignore[no-any-return]

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        # set split_channels checkbox
        if nmm_meta := value.metadata.get(NAPARI_MM_META):
            self.checkBox_split_channels.setChecked(
                nmm_meta.get("split_channels", False)
            )
        super().setValue(value)
