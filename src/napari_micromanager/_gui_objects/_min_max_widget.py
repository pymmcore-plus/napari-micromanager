from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Iterable

from qtpy.QtGui import QColor
from qtpy.QtWidgets import QLabel, QScrollArea, QWidget

if TYPE_CHECKING:
    from napari.layers import Image

QCOLORS = set(QColor.colorNames())


class MinMax(QScrollArea):
    """A Widget to display min and max layer grey values."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self._label = QLabel()
        self.setWidget(self._label)

    def update_from_layers(self, layers: Iterable[Image]) -> None:
        """Update the minmax label based on data from layers."""
        min_max_txt = "(min, max):  "
        for layer in layers:
            col = col if (col := layer.colormap.name) in QCOLORS else "gray"
            try:
                minmax = tuple(layer._calc_data_range(mode="slice"))
                min_max_txt += f' <font color="{col}">{minmax}</font>'
            except Exception:
                warnings.warn("cannot update minmax. napari api changed?", stacklevel=2)

        self._label.setText(min_max_txt)
