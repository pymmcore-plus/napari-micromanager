from typing import Optional

from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QWidget

from micromanager_gui import _core
from micromanager_gui._util import ComboMessageBox


class ChannelWidget(QWidget):
    """Channel selector widget.

    Parameters
    ----------
    objective_device : Optional[str]
        Device label for the objective device, by default will be guessed using
        `mmc.guessObjectiveDevices`, and a dialog will be presented if there are
        multiples
    parent : Optional[QWidget]
        Optional parent widget, by default None
    """

    def __init__(
        self,
        channel_group: str = None,
        parent: Optional[QWidget] = None,
        mmcore: Optional[CMMCorePlus] = None,
    ):

        super().__init__(parent)
        self._mmc = mmcore or _core.get_core_singleton()

        self._channel_group = channel_group or self._get_channel_group()

    def _get_channel_group(self) -> Optional[str]:

        candidates = self._mmc.getOrGuessChannelGroup()

        if len(candidates) == 1:
            return candidates[0]
        elif candidates:
            dialog = ComboMessageBox(candidates, "Select Objective Device:", self)
            if dialog.exec_() == dialog.DialogCode.Accepted:
                return dialog.currentText()
        return None

    # def _refresh_channel_list(self):
    #     guessed_channel_list = self._mmc.getOrGuessChannelGroup()

    #     if not guessed_channel_list:
    #         return

    #     if len(guessed_channel_list) == 1:
    #         self._set_channel_group(guessed_channel_list[0])
    #     else:
    #         # if guessed_channel_list has more than 1 possible channel group,
    #         # you can select the correct one through a combobox
    #         ch = SelectDeviceFromCombobox(
    #             guessed_channel_list,
    #             "Select Channel Group:",
    #             self,
    #         )
    #         ch.val_changed.connect(self._set_channel_group)
    #         ch.show()

    # def _set_channel_group(self, guessed_channel: str):
    #     channel_group = guessed_channel
    #     self._mmc.setChannelGroup(channel_group)
    #     channel_list = self._mmc.getAvailableConfigs(channel_group)
    #     with blockSignals(self.tab_wdg.snap_channel_comboBox):
    #         self.tab_wdg.snap_channel_comboBox.clear()
    #         self.tab_wdg.snap_channel_comboBox.addItems(channel_list)
    #         self.tab_wdg.snap_channel_comboBox.setCurrentText(
    #             self._mmc.getCurrentConfig(channel_group)
    #         )

    # def _on_config_set(self, groupName: str, configName: str):
    #     if groupName == self._mmc.getOrGuessChannelGroup():
    #         with blockSignals(self.tab_wdg.snap_channel_comboBox):
    #             self.tab_wdg.snap_channel_comboBox.setCurrentText(configName)

    # def _channel_changed(self, newChannel: str):
    #     self._mmc.setConfig(self._mmc.getChannelGroup(), newChannel)
