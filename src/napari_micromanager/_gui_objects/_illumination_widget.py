from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, PropertyType
from pymmcore_widgets import PropertiesWidget

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget


class IlluminationWidget(PropertiesWidget):
    """Sliders widget to control illumination."""

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ):
        super().__init__(
            property_name_pattern="(Intensity|Power|test)s?",
            property_type={PropertyType.Integer, PropertyType.Float},
            parent=parent,
            mmcore=mmcore,
        )
