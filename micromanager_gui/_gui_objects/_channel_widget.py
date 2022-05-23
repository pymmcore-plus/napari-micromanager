from typing import Optional, Union

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtWidgets import QComboBox, QVBoxLayout, QWidget

from micromanager_gui import _core

from .._core_widgets._presets_widget import PresetsWidget
from .._util import ComboMessageBox


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
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):

        super().__init__(parent)
        self._mmc = mmcore or _core.get_core_singleton()

        self._channel_group = channel_group or self._get_channel_group()

        self.channel_wdg = self._create_channel_widget(self._channel_group)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(self.channel_wdg)

        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)
        self._mmc.events.channelGroupChanged.connect(self._on_channel_group_changed)
        self._mmc.events.configSet.connect(self._on_channel_set)

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
            channel_wdg = PresetsWidget(channel_group)
        else:
            channel_wdg = QComboBox()
            channel_wdg.setEnabled(False)
        return channel_wdg

    def _on_sys_cfg_loaded(self):
        channel_group = self._channel_group or self._get_channel_group()
        if channel_group is not None:
            self._mmc.setChannelGroup(channel_group)
            # if the channel_group name is the same as the one in the previously
            # loaded cfg and it contains different presets, the 'channelGroupChanged'
            # signal is not emitted and we get a ValueError. So we need to call:
            self._on_channel_group_changed(channel_group)

    def _on_channel_set(self, group: str, preset: str):
        ch = self._mmc.getChannelGroup()
        if group != ch:
            return
        for d in self._mmc.getConfigData(ch, preset):
            _dev = d[0]
            _type = self._mmc.getDeviceType(_dev)
            if _type is DeviceType.Shutter:
                self._mmc.setProperty("Core", "Shutter", _dev)
                break

    def _on_channel_group_changed(self, new_channel_group: str):
        """When Channel group is changed, recreate combo."""
        self.channel_wdg.setParent(None)
        self.channel_wdg.deleteLater()
        self._update_widget(new_channel_group)

    def _update_widget(self, channel_group):
        self.channel_wdg = self._create_channel_widget(channel_group)
        self.layout().addWidget(self.channel_wdg)

    def _disconnect_from_core(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_sys_cfg_loaded)
        self._mmc.events.channelGroupChanged.disconnect(self._on_channel_group_changed)
        self._mmc.events.configSet.disconnect(self._on_channel_set)
