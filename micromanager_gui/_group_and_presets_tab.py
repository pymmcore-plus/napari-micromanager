from __future__ import annotations

from typing import TYPE_CHECKING, Any

from magicgui.widgets import (
    ComboBox,
    Container,
    FloatSlider,
    LineEdit,
    PushButton,
    Slider,
    Table,
    Widget,
)
from PyQt5.QtWidgets import QHBoxLayout
from qtpy import QtWidgets as QtW

# from ._properties_table_with_checkbox import GroupConfigurations

if TYPE_CHECKING:
    from pymmcore_plus import RemoteMMCore


WDG_TYPE = (FloatSlider, Slider, LineEdit)


class MainTable(Table):
    def __init__(self, mmcore: RemoteMMCore()) -> None:
        super().__init__()
        self.mmcore = mmcore
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        vh = self.native.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self.native.setEditTriggers(QtW.QTableWidget.NoEditTriggers)


class GroupPresetWidget(QtW.QWidget):
    def __init__(self, mmcore: RemoteMMCore, parent=None):
        super().__init__(parent)
        self._mmc = mmcore

        # connect mmcore signals
        # sig = self._mmc.events

        self.tb = MainTable(self._mmc)
        self.tb.column_headers = ("Groups", "Presets")
        self.tb.show()

        self.new_btn = PushButton(text="New Group/Preset")
        self.edit_btn = PushButton(text="Edit Group/Preset")
        self.delete_gp_btn = PushButton(text="- Group")
        self.delete_gp_btn.clicked.connect(self._delete_selected_group)
        self.delete_ps_btn = PushButton(text="- Preset")
        self.delete_ps_btn.clicked.connect(self._delete_selected_preset)

        buttons = Container(
            widgets=[
                self.new_btn,
                self.edit_btn,
                self.delete_gp_btn,
                self.delete_ps_btn,
            ],
            labels=False,
            layout="horizontal",
        )

        self.group_presets_widget = Container(
            widgets=[self.tb, buttons], labels=True, layout="vertical"
        )
        self.group_presets_widget.margins = 0, 0, 0, 0
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.group_presets_widget.native)

        self._add_to_table()

        # @sig.configSet.connect
        # def _on_cfg_set(group: str, preset: str):
        #     print(f"[tab] New group cfg set: {group} -> {preset}")
        #     channel_group = self._mmc.getChannelGroup()
        #     if group == channel_group:
        #         rows = self.tb.shape[0]
        #         for row in range(rows):
        #             gp, wdg = self.tb.data[row]
        #             if gp == group:
        #                 wdg.value = self._mmc.getCurrentConfig(gp)
        #                 return

    def _add_to_table(self):
        groups = self._mmc.getAvailableConfigGroups()
        data = []
        for group in groups:
            presets = self._mmc.getAvailableConfigs(group)
            wdg = self._set_widget(group, presets)
            data.append([group, wdg])
        self.tb.value = {"data": data, "index": [], "columns": ["Groups", "Presets"]}

        self._update_group_table_status()

    def _update_group_table_status(self):

        for row in range(self.tb.shape[0]):

            group, wdg = self.tb.data[row]

            if isinstance(wdg, WDG_TYPE):
                preset = self._mmc.getPropertyFromCache(
                    wdg.annotation[0], wdg.annotation[1]
                )

                if preset:
                    dev, prop = wdg.annotation
                    if wdg.name == "Slider":
                        val = int(preset)
                    elif wdg.name == "FloatSlider":
                        val = float(preset)
                    elif wdg.name == "LineEdit":
                        val = str(preset)
                    wdg.value = val
                    self._mmc.setProperty(dev, prop, val)

            else:
                preset = self._mmc.getCurrentConfigFromCache(group)
                if preset:
                    wdg.value = preset
                    self._mmc.setConfig(group, preset)

    def _get_cfg_data(self, group, preset):
        for n, key in enumerate(self._mmc.getConfigData(group, preset)):
            dev = key[0]
            prop = key[1]
            val = key[2]
        return dev, prop, val, (n + 1)

    def _set_widget(self, group, presets) -> Widget:
        wdg = None

        dev, prop, val, count = self._get_cfg_data(group, presets[0])

        if len(presets) > 1:
            wdg = ComboBox(choices=presets, name="ComboBox", annotation=[dev, prop])
        else:
            if count > 1 or self._mmc.getAllowedPropertyValues(dev, prop):
                wdg = ComboBox(choices=presets, name="ComboBox", annotation=[dev, prop])
            elif self._mmc.hasPropertyLimits(dev, prop):
                val_type = self._mmc.getPropertyLowerLimit(dev, prop)
                if isinstance(val_type, float):
                    wdg = FloatSlider(
                        value=float(val),
                        min=float(self._mmc.getPropertyLowerLimit(dev, prop)),
                        max=float(self._mmc.getPropertyUpperLimit(dev, prop)),
                        label=str(prop),
                        name="FloatSlider",
                        annotation=[dev, prop],
                    )
                else:
                    wdg = Slider(
                        value=int(val),
                        min=int(self._mmc.getPropertyLowerLimit(dev, prop)),
                        max=int(self._mmc.getPropertyUpperLimit(dev, prop)),
                        label=str(prop),
                        name="Slider",
                        annotation=[dev, prop],
                    )
            else:
                wdg = LineEdit(value=str(val), name="LineEdit", annotation=[dev, prop])

        @wdg.changed.connect
        def _on_change(value: Any):
            if wdg.name == "ComboBox":
                self._mmc.setConfig(group, value)
            else:
                if wdg.name == "FloatSlider":
                    v = float(value)
                elif wdg.name == "LineEdit":
                    v = str(value)
                elif wdg.name == "Slider":
                    v = int(value)
                self._mmc.setProperty(dev, prop, v)

        return wdg

    def _delete_selected_group(self):
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            self.tb.native.removeRow(row_idx)

    def _delete_selected_preset(self):  # sourcery skip: merge-duplicate-blocks
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            wdg = self.tb.data[row_idx, 1]  # [r, c]
            if isinstance(wdg, ComboBox):
                if len(wdg.choices) == 1:
                    self.tb.native.removeRow(row_idx)
                else:
                    wdg.del_choice(wdg.value)
            else:
                self.tb.native.removeRow(row_idx)
