from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import ShuttersWidget
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QWidget


class MMShuttersWidget(QWidget):
    """Create shutter widget."""

    def __init__(
        self, *, parent: Optional[QWidget] = None, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(parent=parent)

        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(3)
        self.layout().setContentsMargins(0, 0, 0, 0)
        sizepolicy_btn = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setSizePolicy(sizepolicy_btn)

        self._mmc = mmcore or CMMCorePlus.instance()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)
        self._on_cfg_loaded()

    def _on_cfg_loaded(self) -> None:
        self._clear()

        if not self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice):
            # FIXME:
            # ShuttersWidget has not been tested with an empty device label...
            # it raises all sorts of errors.
            # if we want to have a "placeholder" widget, it needs more testing.

            # empty_shutter = ShuttersWidget("")
            # self.layout().addWidget(empty_shutter)
            return

        shutters_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice))
        for d in shutters_devs:
            props = self._mmc.getDevicePropertyNames(d)
            if bool([x for x in props if "Physical Shutter" in x]):
                shutters_devs.remove(d)
                shutters_devs.insert(0, d)

        for idx, shutter in enumerate(shutters_devs):
            if idx == len(shutters_devs) - 1:
                s = ShuttersWidget(shutter)
            else:
                s = ShuttersWidget(shutter, autoshutter=False)
            s.button_text_open = shutter
            s.button_text_closed = shutter
            self.layout().addWidget(s)

    def _clear(self) -> None:
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.deleteLater()
