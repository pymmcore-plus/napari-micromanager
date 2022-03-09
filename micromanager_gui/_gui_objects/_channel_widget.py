from typing import Optional, Union

from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget

from micromanager_gui import _core
from micromanager_gui._core_widgets._presets_widget import PresetsWidget
from micromanager_gui._util import ComboMessageBox


class ChannelWidget(QWidget):
    """Channel selector widget.

    Parameters
    ----------
    channel_group : Optional[str]
        Name of the group defining the microscope channels, by default will be guessed
        using `mmc.getOrGuessChannelGroup`, and a dialog will be presented if there are
        multiples
    parent : Optional[QWidget]
        Optional parent widget, by default None
    """

    def __init__(
        self,
        channel_group: Optional[str] = None,
        parent: Optional[QWidget] = None,
        mmcore: Optional[CMMCorePlus] = None,
    ):

        super().__init__(parent)
        self._mmc = mmcore or _core.get_core_singleton()

        self._channel_group = channel_group or self._get_channel_group()

        self.channel_combo = self._create_channel_widget(self._channel_group)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(self.channel_combo)

        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)
        self._mmc.events.channelGroupChanged.connect(self._on_channel_group_changed)
        self.destroyed.connect(self._disconnect_from_core)
        self._on_sys_cfg_loaded()

    def _get_channel_group(self) -> Optional[str]:
        candidates = self._mmc.getOrGuessChannelGroup()
        if len(candidates) == 1:
            return candidates[0]
        elif candidates:
            dialog = ComboMessageBox(candidates, "Select Channel Group:", self)
            if dialog.exec_() == dialog.DialogCode.Accepted:
                return dialog.currentText()
        return None

    def _create_channel_widget(
        self, channel_group: str
    ) -> Union[PresetsWidget, QComboBox]:
        if channel_group:
            channel_combo = PresetsWidget(channel_group, text_color="white")
        else:
            channel_combo = QComboBox()
            channel_combo.setEnabled(False)
        return channel_combo

    def _on_sys_cfg_loaded(self):
        self._clear_previous_device_widget()
        channel_group = self._channel_group or self._get_channel_group()
        self.channel_combo = self._create_channel_widget(channel_group)
        self.layout().addWidget(self.channel_combo)

    def _on_channel_group_changed(self, new_channel_group: str):
        """When Channel group is changed, recreate combo."""
        if isinstance(self.channel_combo, QComboBox):
            self._clear_previous_device_widget()
            self.channel_combo = self._create_channel_widget(new_channel_group)
            self.layout().addWidget(self.channel_combo)
        else:
            self.channel_combo.refresh()

    def _clear_previous_device_widget(self):
        self.channel_combo.setParent(None)
        self.channel_combo.deleteLater()

    def _disconnect_from_core(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_sys_cfg_loaded)
        self._mmc.events.channelGroupChanged.disconnect(self._on_channel_group_changed)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = ChannelWidget()
    win.show()
    sys.exit(app.exec_())
