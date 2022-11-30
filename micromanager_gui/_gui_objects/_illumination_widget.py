import re
from typing import Optional

from pymmcore_plus import CMMCorePlus, PropertyType
from pymmcore_widgets import PropertyWidget
from qtpy.QtWidgets import QDialog, QGridLayout, QLabel, QSizePolicy, QWidget

from .._util import iter_dev_props


class IlluminationWidget(QDialog):
    """Sliders widget to control illumination."""

    def __init__(
        self,
        property_regex: str = "(Intensity|Power|test)s?",
        *,
        parent: Optional[QWidget] = None,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent=parent)

        self.setLayout(QGridLayout())

        self.ptrn = re.compile(property_regex, re.IGNORECASE)
        self._mmc = mmcore or CMMCorePlus.instance()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

        self.destroyed.connect(self._disconnect)

        self._on_cfg_loaded()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _create_wdg(self) -> None:

        lights = [
            dp
            for dp in iter_dev_props(self._mmc)
            if self.ptrn.search(dp[1])
            and self._mmc.hasPropertyLimits(*dp)
            and self._mmc.getPropertyType(*dp)
            in {PropertyType.Integer, PropertyType.Float}
        ]
        for i, (dev, prop) in enumerate(lights):
            self.layout().addWidget(QLabel(f"{dev}::{prop}"), i, 0)
            self.layout().addWidget(PropertyWidget(dev, prop, mmcore=self._mmc), i, 1)

    def _on_cfg_loaded(self) -> None:
        self._clear()
        self._create_wdg()

    def _clear(self) -> None:
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.deleteLater()

    def _disconnect(self) -> None:
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_cfg_loaded)
